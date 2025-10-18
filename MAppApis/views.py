from time import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from MAppApis.serializers import *
from django.http import HttpResponseForbidden
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.permissions import IsAuthenticated
from FWC2025.env_details import *
from fwc.models import *
from utils.token_validation_utils import *
from utils.generate_utils import GenerateOTP
from utils.firebase_utils import *
from datetime import datetime, timedelta
from fwc.helpers import *
from django.core.mail import send_mail
from django.db.models import Q
from fwc.helpers import *
import hashlib
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
import datetime


class DummyUser:
    def __init__(self, username):
        self.username = username
        self.id = 1

@method_decorator(csrf_exempt, name='dispatch')
class GenerateAppTokenView(TokenObtainPairView):
    serializer_class = GenerateAppTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        username = request.headers.get('username')
        password = request.headers.get('password')
        
        if (username != FWC_APP_API_USERNAME or password != FWC_APP_API_PASSWORD):
            return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer.is_valid(raise_exception=True)
        user = DummyUser(username)
        token = AccessToken.for_user(user)

        token['deviceid'] = request.data.get("deviceid")
        token['username'] = username

        token.set_exp(lifetime=timedelta(minutes=15))

        return Response({"access_token": str(token)}, status=status.HTTP_200_OK)
    
    
class CheckFideIDAPIView(APIView):
    """
    API to check if FIDE ID exists in FideIDMst and get player details
    """
    
    def post(self, request):
        validate_app_and_device_with_token(request)
        serializer = FideIDCheckSerializer(data=request.data)
        
        if serializer.is_valid():
            fide_id = serializer.validated_data['fide_id']
            
            try:
                # Check if FIDE ID exists in FideIDMst
                fide_record = FideIDMst.objects.filter(
                    fide_id=fide_id, 
                    status_flag=1
                ).first()
                
                if not fide_record:
                    return Response({
                        "exists": False,
                        "message": "Invalid FIDE ID"
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # Check if player already registered in Players table
                existing_player = Players.objects.filter(fide_id=fide_id, status_flag=1).first()
                
                if existing_player:
                    response_data = {
                        "player_registered": True,
                        "player_details": {
                            "fide_id": fide_record.fide_id,
                            "name": existing_player.name,
                            "email": existing_player.email,
                        }
                    }
                    response_data["message"] = "Player already registered"
                else:
                    response_data = {
                        "player_registered": False,
                        "message": "Player not registered"
                    }
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "error": "Server error occurred",
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
     

class SendOTPAPIView(APIView):
    def post(self, request):
        # Validate based on OTP type
        otp_type = request.data.get('otp_type')
        
        if otp_type in ['registration', 'forgot_password']:
            validate_app_and_device_with_token(request)
        elif otp_type in ['change_password']:
            validate_email_and_device_with_token(request)
        
        serializer = PlayerOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            otp_type = serializer.validated_data['otp_type']
            fide_id = serializer.validated_data.get('fide_id')

            if otp_type == 'forgot_password':
                if not email:
                    return Response({
                        "message": "User is not registered or Inactive.",
                        "otp_type": otp_type
                    }, status=status.HTTP_201_CREATED)
                
                # Verify the player exists and is active
                try:
                    player = Players.objects.get(email=email, status_flag=1)
                    if not fide_id:
                        fide_id = player.fide_id
                except Players.DoesNotExist:
                    return Response({
                        "message": "User is not registered or Inactive.",
                        "otp_type": otp_type
                    }, status=status.HTTP_201_CREATED)

            # Generate OTP
            otp = GenerateOTP.generate_otp()
            enc_otp = str_encrypt(str(otp))

            # Update or create OTP record
            existing = CustomerLoginOtpVerification.objects.filter(
                email=email, status_flag=1, flag=otp_type
            )
            
            if existing.exists():
                existing.update(
                    secureotp=enc_otp,
                    source='WebApp',
                    updated_on=datetime.datetime.now(),
                    flag=otp_type,
                    support_remarks=otp,
                )
            else:
                CustomerLoginOtpVerification.objects.create(
                    email=email,
                    secureotp=enc_otp,
                    source='WebApp',
                    flag=otp_type,
                    support_remarks=otp,
                )
            
            # Send email based on OTP type
            self.send_otp_email(email, otp, otp_type, fide_id)

            return Response({
                "message": "OTP sent successfully",
                "otp_type": otp_type
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def send_otp_email(self, email, otp, otp_type, fide_id):
        """Send OTP email based on type"""
        email_config = {
            'registration': {
                'template': 'email.html',
                'subject': 'Registration OTP - FIDE World Cup 2025',
                'email_type': 'REGISTRATION'
            },
            'change_password': {
                'template': 'change_password_email.html',
                'subject': 'Password Change OTP - FIDE World Cup 2025',
                'email_type': 'CHANGE_PASSWORD'
            },
            'forgot_password': {
                'template': 'forget_password_email.html',
                'subject': 'Password Reset OTP - FIDE World Cup 2025',
                'email_type': 'FORGOT_PASSWORD'
            }
        }
        
        config = email_config.get(otp_type, email_config['registration'])
        
        # Render HTML email template
        html_message = render_to_string(
            config['template'],
            {
                'otp': otp,
                'fide_id': fide_id,
                'email': email
            }
        )
                
        # Create email log entry
        email_log = EmailLog.objects.create(
            email_type=config['email_type'],
            subject=config['subject'],
            recipient_email=email,
            status='PENDING',
            html_content=html_message,
            text_content='',
        )

        try:
            send_mail(
                subject=config['subject'],
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            email_log.status = 'SENT'
            email_log.save()
            
        except Exception as e:
            email_log.status = 'FAILED'
            email_log.error_message = str(e)
            email_log.save()
            raise
    

    
    
def verify_otp(email, otp, flag='registration'):
    """
    Verify OTP for registration
    """
    try:
        # Find the latest OTP for this email and flag
        otp_record = CustomerLoginOtpVerification.objects.filter(
            email=email,
            flag=flag,
            status_flag=1
        ).order_by('-created_on').first()
        
        if not otp_record:
            return False, "OTP Invalid or Expired"
        
        # Decrypt and verify OTP
        crypted_otp = str_encrypt(otp)
        
        if otp_record.secureotp == crypted_otp:
            # Mark OTP as used
            otp_record.status_flag = 0
            otp_record.updated_on = timezone.now()
            otp_record.save()
            return True, "OTP verified successfully"
        else:
            return False, "Invalid OTP"
            
    except Exception as e:
        return False, f"OTP verification failed: {str(e)}"
    

class RegisterPlayerAPIView(APIView):
    """
    API to register a new player with OTP verification
    """
    
    @transaction.atomic
    def post(self, request):
        # validate_app_and_device_with_token(request)
        serializer = PlayerRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            name = serializer.validated_data['name']
            password = serializer.validated_data['password']
            fide_id = serializer.validated_data['fide_id']
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            
            try:
                # Step 1: Verify OTP
                otp_valid, otp_message = verify_otp(email, otp, 'registration')
                if not otp_valid:
                    return Response({
                        "error": "OTP verification failed",
                        "message": otp_message
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Step 2: Check if FIDE ID exists
                fide_record = FideIDMst.objects.filter(
                    fide_id=fide_id, 
                    status_flag=1
                ).first()
                
                if not fide_record:
                    return Response({
                        "error": "FIDE ID not found",
                        "message": "The provided FIDE ID is not registered. Please check your FIDE ID or contact administrators."
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # Step 3: Check if player already exists
                existing_player = Players.objects.filter(fide_id=fide_id,status_flag=1).first()
                
                # Step 4: Create or update player
                if existing_player:
                    if existing_player.email != email:
                        return Response({
                            "error": "Email mismatch",
                            "message": "The provided email does not match the existing player's email and fide id."
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Update existing player credentials
                    existing_player.name = name
                    existing_player.securepassword = str_encrypt(password)
                    existing_player.updated_on = timezone.now()
                    existing_player.save()
                    
                    return Response({
                        "success": True,
                        "message": "Player credentials updated successfully",
                        "player_id": existing_player.id,
                        "action": "updated"
                    }, status=status.HTTP_200_OK)
                    
                else:    
                    # Create player
                    player = Players.objects.create(
                        name=name,
                        fide_id=fide_id,
                        email=email,
                        securepassword=str_encrypt(password),
                        created_on=timezone.now()
                    )
                    
                    return Response({
                        "success": True,
                        "message": "Player registered successfully",
                        "action": "created"
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({
                    "error": "Registration failed",
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class PlayerLoginView(APIView):
    def post(self, request):
        validate_app_and_device_with_token(request)
        serializer = PlayerLoginSerializer(data=request.data)
        if serializer.is_valid():
            player = serializer.validated_data['player']
            deviceid = serializer.validated_data['deviceid']
            
            new_customer = DummyUser(player)

            access = AccessToken.for_user(new_customer)

            # Custom claims
            access['email'] = player.email
            access['deviceid'] = deviceid
            access['fide_id'] = player.fide_id

            # Expiry
            access.set_exp(lifetime=timedelta(days=30))
            
            device_token = serializer.validated_data.get('device_token', None)

            if device_token:  
                # update or create device token for the user  
                obj, created = UserDeviceToken.objects.update_or_create(
                    user_email=player.email,
                    defaults={"device_token": device_token}
                )

                if not created:
                    obj.updated_on = timezone.now()
                    obj.save()
                
            return Response({
                "access_token": str(access),
                "player": {
                    "id": player.id,
                    "fide_id": player.fide_id,
                    "name": player.name,
                    "email": player.email,
                },
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        validate_email_and_device_with_token(request)
        user_email = request.data.get('email')
        try:
            token_obj = UserDeviceToken.objects.filter(user_email=user_email).first()
            if token_obj:
                token_obj.delete()
                
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": {"message": str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
        


class PlayerTransportationAPIView(APIView):
    """
    POST API to fetch transportation details grouped by roaster for a specific player
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        serializer = PlayerIDRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Invalid request data",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        player = serializer.validated_data['player_id']
        print("player_id", player.id)
        
        try:            
            # Get query parameters from POST data for filtering
            status_filter = request.data.get('status', None)
            transportation_type = request.data.get('transportation_type', None)
            date_from = request.data.get('date_from', None)
            date_to = request.data.get('date_to', None)
            vehicle_type = request.data.get('vehicle_type', None)
            
            # Get all transportation details for this player
            player_transports = PlayerTransportationDetails.objects.filter(
                playerId=player,
                status_flag=1
            ).select_related('roasterId', 'transportationTypeId')
            
            # Apply filters to player transports
            if status_filter:
                player_transports = player_transports.filter(status=status_filter)
            
            if transportation_type:
                player_transports = player_transports.filter(transportationTypeId_id=transportation_type)
            
            if date_from:
                player_transports = player_transports.filter(travel_date__gte=date_from)
            
            if date_to:
                player_transports = player_transports.filter(travel_date__lte=date_to)
            
            # Get unique roasters from the filtered transports
            roaster_ids = player_transports.values_list('roasterId_id', flat=True).distinct()
            roasters = Roaster.objects.filter(
                id__in=roaster_ids,
                status_flag=1
            ).select_related('transportationTypeId')
            
            # Apply vehicle type filter to roasters
            if vehicle_type:
                roasters = roasters.filter(vechicle_type__icontains=vehicle_type)
            
            # Order roasters by creation date
            roasters = roasters.order_by('-created_on')
            
            # Serialize data with player context
            roaster_serializer = RoasterTransportationSerializer(
                roasters, 
                many=True, 
                context={'player_id': player.id}
            )
            
            # Calculate statistics
            total_roasters = roasters.count()
            total_transports = player_transports.count()
            
            now = timezone.now()
            upcoming_count = player_transports.filter(travel_date__gte=now).count()
            past_count = player_transports.filter(travel_date__lt=now).count()
            
            # Group by status for summary
            status_summary = {}
            for transport in player_transports:
                status_val = transport.status
                status_summary[status_val] = status_summary.get(status_val, 0) + 1
            
            # Prepare response
            response_data = {
                "success": True,
                # "filters_applied": {
                #     "status": status_filter,
                #     "transportation_type": transportation_type,
                #     "date_from": date_from,
                #     "date_to": date_to,
                #     "vehicle_type": vehicle_type
                # },
                # "summary": {
                #     "total_roasters": total_roasters,
                #     "total_transportations": total_transports,
                #     "upcoming_transportations": upcoming_count,
                #     "past_transportations": past_count,
                #     "status_breakdown": status_summary
                # },
                "roasters": roaster_serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Server error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DepartmentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            validate_email_and_device_with_token(request)

            departments = Department.objects.filter(status_flag=1)
            serializer = DepartmentSerializer(departments, many=True)

            return Response(
                {"departments": serializer.data},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": {"message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )
    
      
        
class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        validate_email_and_device_with_token(request)
            
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            otp_valid, otp_message = verify_otp(email, otp, 'change_password')
            if not otp_valid:
                return Response({
                    "error": "OTP verification failed",
                    "message": otp_message
                }, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class ForgetPasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        validate_app_and_device_with_token(request)
            
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            
            otp_valid, otp_message = verify_otp(email, otp, 'forgot_password')
            if not otp_valid:
                return Response({
                    "error": "OTP verification failed",
                    "message": otp_message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class PlayerNotificationListView(APIView):
    """
    POST API to get all announcements where the player has been tagged/recipient
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        serializer = PlayerIDRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Invalid request data",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        player = serializer.validated_data['player_id']
        
        try:
            # Validate player exists and is active
            player = get_object_or_404(Players, id=player.id, status_flag=1)
            
            # Get announcements where player is a recipient
            recipient_announcements = AnnouncementRecipients.objects.filter(
                player=player,
                status_flag=1
            ).select_related('announcement', 'announcement__created_by')
            
            # Get the actual announcements
            announcements = Announcements.objects.filter(
                id__in=recipient_announcements.values_list('announcement_id', flat=True),
                status_flag=1
            ).select_related('created_by').order_by('-created_on')
            
            # Serialize data
            serializer = AnnouncementNotificationSerializer(announcements, many=True)
            
            # Calculate total count
            total_count = announcements.count()
            
            # Prepare response
            response_data = {
                "success": True,
                "notifications_summary": {
                    "total_notifications": total_count
                },
                "notifications": serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Server error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            

class ContactFormView(APIView):
    """
    POST API to handle Get in Touch form submissions
    """
    
    def post(self, request):
        validate_app_and_device_with_token(request)
        serializer = ContactFormSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Extract validated data
            name = serializer.validated_data['name']
            email = serializer.validated_data['email']
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            
            # Create new GetInTouch record
            contact_entry = ContactUs.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message,
                status_flag=1
            )
            
            html_message = render_to_string(
               'contact_us.html',
               {
                    'name': name,
                    'email': email,
                    'subject': subject,
                    'message': message,
                    'submitted_date': timezone.now().strftime("%B %d, %Y at %I:%M %p")
               }
            )
            
            subject = f"Contact Form: {subject}"
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                email_type='CONTACT_US',
                subject=subject,
                recipient_email=CHESS_FWC_2025_EMAIL,
                status='PENDING',
                html_content=html_message,
                text_content="", 
            )

            send_mail(
                subject=subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[CHESS_FWC_2025_EMAIL],
                html_message=html_message,
                fail_silently=False,
            )
            # Update email log with success
            email_log.status = 'SENT'
            email_log.save()
            
            # Prepare success response
            response_data = {
                "success": True,
                "message": "Thank you for contacting us! We will get back to you soon.",
                "contact_id": contact_entry.id,
                "submitted_data": {
                    "name": name,
                    "email": email,
                    "subject": subject
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Failed to submit contact form",
                "message": "An error occurred while processing your request. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

class EnquiryFormView(APIView):
    """
    POST API to submit a new enquiry
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        serializer = EnquiryCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            player_id = serializer.validated_data['player_id']
            message = serializer.validated_data['message']
            
            # Get player instance
            player = Players.objects.get(id=player_id, status_flag=1)
            
            # Create new enquiry
            enquiry = EnquiryDetails.objects.create(
                player=player,
                message=message,
                response="",  # Empty response initially
                status_flag=1
            )
            
            html_message = render_to_string(
               'enquiry_email.html',
               {
                    'player_name': player.name,
                    'player_fide_id': player.fide_id or 'Not provided',
                    'player_email': player.email,
                    'message': message,
                    'submitted_date': timezone.now().strftime("%B %d, %Y at %I:%M %p")
               }
            )
            
            subject = f"Player Enquiry from {player.name}"
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                email_type='ENQUIRY',
                subject=subject,
                recipient_email=CHESS_FWC_2025_EMAIL,
                status='PENDING',
                html_content=html_message,
                text_content="", 
            )

            send_mail(
                subject=subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[CHESS_FWC_2025_EMAIL],
                html_message=html_message,
                fail_silently=False,
            )
            # Update email log with success
            email_log.status = 'SENT'
            email_log.save()
            
            response_data = {
                "success": True,
                "message": "Your enquiry has been submitted successfully. We will respond soon.",
                "enquiry_id": enquiry.id,
                "submitted_data": {
                    "player_id": player_id,
                    "player_name": player.name,
                    "message_preview": message[:100] + "..." if len(message) > 100 else message
                },
                "timestamp": enquiry.created_on.isoformat()
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Enquiry submission failed",
                "message": "An error occurred while submitting your enquiry. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
            
class PlayerEnquiriesListView(APIView):
    """
    POST API to get all enquiries of a specific player
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        player_id = request.data.get('player_id')
        
        if not player_id:
            return Response({
                "success": False,
                "error": "Player ID is required",
                "message": "Please provide player_id in the request body"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate player exists
            player = get_object_or_404(Players, id=player_id, status_flag=1)
            
            # Get all enquiries for this player
            enquiries = EnquiryDetails.objects.filter(
                player=player,
                status_flag=1
            ).select_related('player').order_by('-created_on')
            
            # Serialize data
            serializer = EnquiryListSerializer(enquiries, many=True)
            
            # Calculate statistics
            total_enquiries = enquiries.count()
            responded_enquiries = enquiries.exclude(response="").count()
            pending_enquiries = total_enquiries - responded_enquiries
            
            response_data = {
                "success": True,
                "enquiries_summary": {
                    "total_enquiries": total_enquiries,
                    "responded_enquiries": responded_enquiries,
                    "pending_enquiries": pending_enquiries
                },
                "enquiries": serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Failed to fetch enquiries",
                "message": "An error occurred while fetching your enquiries. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    

class ComplaintListView(APIView):
    """
    POST API for player to view all their complaints with conversations
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        player_id = request.data.get('player_id')
        
        if not player_id:
            return Response({
                "success": False,
                "error": "Player ID is required",
                "message": "Please provide player_id in the request body"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate player exists
            player = get_object_or_404(Players, id=player_id, status_flag=1)
            
            # Get all complaints for this player
            complaints = PlayerComplaint.objects.filter(
                player=player,
                status_flag=1
            ).select_related('player', 'department').prefetch_related('conversations').order_by('-created_on')
            
            # Serialize data
            serializer = ComplaintListSerializer(complaints, many=True)
            
            response_data = {
                "success": True,
                "complaints": serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            print("Exception: ", e)
            return Response({
                "success": False,
                "error": "Failed to fetch complaints",
                "message": "An error occurred while fetching your complaints. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
class RaiseComplaintView(APIView):
    """
    POST API for player to raise a new complaint
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        player_id = request.data.get('player_id')
        
        if not player_id:
            return Response({
                "success": False,
                "error": "Player ID is required",
                "message": "Please provide player_id in the request body"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RaiseComplaintSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            description = serializer.validated_data['description']
            department_id = serializer.validated_data['department_id']
            
            # Get player and department instances
            player = Players.objects.get(id=player_id, status_flag=1)
            department = Department.objects.get(id=department_id, status_flag=1)
            
            # Create new complaint
            complaint = PlayerComplaint.objects.create(
                player=player,
                description=description,
                department=department,
                status='OPEN',
                status_flag=1
            )
            
            context = {
                'player_name': player.name,
                'player_fide_id': player.fide_id or 'Not provided',
                'player_email': player.email,
                'player_id': player.id,
                'complaint_id': complaint.id,
                'description': description,
                'department_name': department.name,
                'status': complaint.status,
                'submitted_date': timezone.now().strftime("%B %d, %Y at %I:%M %p"),
            }
            
            # Render HTML email template
            html_message = render_to_string('complaint_email.html', context)

            subject = f"COMPLAINT from {player.name} - #C{complaint.id} - {department.name}"
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                email_type='COMPLAINT',
                subject=subject,
                recipient_email=CHESS_FWC_2025_EMAIL,
                status='PENDING',
                html_content=html_message,
                text_content="", 
            )

            send_mail(
                subject=subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[CHESS_FWC_2025_EMAIL],
                html_message=html_message,
                fail_silently=False,
            )
            # Update email log with success
            email_log.status = 'SENT'
            email_log.save()
            
            response_data = {
                "success": True,
                "message": "Your complaint has been submitted successfully. We will address it soon.",
                "complaint_id": complaint.id,
                "complaint_data": {
                    "department": department.name,
                    "status": "OPEN"
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Department.DoesNotExist:
            return Response({
                "success": False,
                "error": "Department not found",
                "message": "The specified department does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Complaint submission failed",
                "message": "An error occurred while submitting your complaint. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
class EditComplaintRemarkView(APIView):
    """
    POST API for player to reply to their existing complaint
    """
    
    def post(self, request):
        validate_email_and_device_with_token(request)
        player_id = request.data.get('player_id')
        
        if not player_id:
            return Response({
                "success": False,
                "error": "Player ID is required",
                "message": "Please provide player_id in the request body"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ReplyToComplaintSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            complaint_id = serializer.validated_data['complaint_id']
            message = serializer.validated_data['message']
            
            # Get player and complaint
            player = Players.objects.get(id=player_id, status_flag=1)
            complaint = PlayerComplaint.objects.get(id=complaint_id, status_flag=1)
            
            # Verify the complaint belongs to this player
            if complaint.player.id != player.id:
                return Response({
                    "success": False,
                    "error": "Access denied",
                    "message": "You can only reply to your own complaints"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Create conversation entry
            conversation = PlayerComplaintConversation.objects.create(
                complaint=complaint,
                sender_player=player,
                message=message,
                status_flag=1
            )
            
            # Update complaint timestamp
            complaint.updated_on = timezone.now()
            complaint.save()
            
            response_data = {
                "success": True,
                "message": "Your response has been added to the complaint.",
                "conversation_id": conversation.id,
                "complaint_id": complaint_id
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Players.DoesNotExist:
            return Response({
                "success": False,
                "error": "Player not found",
                "message": "The specified player does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except PlayerComplaint.DoesNotExist:
            return Response({
                "success": False,
                "error": "Complaint not found",
                "message": "The specified complaint does not exist or is inactive"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Failed to add response",
                "message": "An error occurred while adding your response. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            

class HomeImageDataView(APIView):
    """
    API to return all images from static/home folder
    """
    
    def post(self, request):
        try:
            validate_app_and_device_with_token(request)
            # Define the path to the home images folder
            home_images_path = os.path.join(settings.STATIC_ROOT, 'home')
            
            # If STATIC_ROOT doesn't exist, try STATICFILES_DIRS
            if not os.path.exists(home_images_path):
                home_images_path = self.find_home_images_path()
            
            if not home_images_path or not os.path.exists(home_images_path):
                return Response({
                    "success": False,
                    "error": "Home images directory not found",
                    "message": "The home images directory does not exist"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get all image files from the directory
            image_files = []
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            
            for filename in os.listdir(home_images_path):
                file_path = os.path.join(home_images_path, filename)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext in allowed_extensions:
                        # Create relative URL for the image
                        relative_url = f"static/home/{filename}"
                        absolute_url = request.build_absolute_uri(settings.STATIC_URL + f"home/{filename}")
                        
                        image_files.append({
                            "absolute_url": absolute_url
                        })
            
            
            response_data = {
                "success": True,
                "images_count": len(image_files),
                "images": image_files
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Failed to fetch home images",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def find_home_images_path(self):
        """
        Find the home images path in STATICFILES_DIRS
        """
        if hasattr(settings, 'STATICFILES_DIRS'):
            for static_dir in settings.STATICFILES_DIRS:
                home_path = os.path.join(static_dir, 'home')
                if os.path.exists(home_path):
                    return home_path
        
        # Also check in base static directory
        base_home_path = os.path.join(settings.BASE_DIR, 'static', 'home')
        if os.path.exists(base_home_path):
            return base_home_path
        
        return None

class DepartureDetailsAPIView(APIView):
    
    def post(self, request, player_id=None):
        """
        Create/Update departure details for a player
        """
        try:
            validate_email_and_device_with_token(request)
            
            if player_id is None:
                player_id = request.data.get('player_id')
            
            if not player_id:
                return Response(
                    {"error": "Player ID is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            player = get_object_or_404(Players, id=player_id)
            departure_data = request.data.copy()
            
            if 'departure_flight_date' in departure_data:
                player.departure_flight_date = departure_data['departure_flight_date']
            if 'departure_flight_time' in departure_data:
                player.departure_flight_time = departure_data['departure_flight_time']
            if 'departure_airport' in departure_data:
                player.departure_airport = departure_data['departure_airport']
            
            player.updated_on = timezone.now()
            player.save()
            
            return Response({
                "message": "Departure details updated successfully",
                "data": {
                    "id": player.id,
                    "departure_flight_date": player.departure_flight_date,
                    "departure_flight_time": player.departure_flight_time,
                    "departure_airport": player.departure_airport,
                }
            }, status=status.HTTP_200_OK)
            
        except Players.DoesNotExist:
            return Response(
                {"error": "Player not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {"error": dict(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )