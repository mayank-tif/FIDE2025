import json
import time
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, View, ListView
from utils.firebase_utils import send_push_notification
from .models import *
from django.urls import reverse
from django.core.paginator import Paginator
import io
import base64
from django.db.models import Count, Sum, Q, OuterRef, Subquery
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from .helpers import * 
import pandas as pd
import requests
from django.contrib.auth import logout
from django.contrib import messages
from .form import *
import os
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Prefetch
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.core.files.base import ContentFile
from FWC2025.env_details import *
import xlsxwriter
from datetime import datetime


per_page = 50


class View_platformlogin(TemplateView):

    def get(self, request):
        # Check if user is already logged in
        msg = request.GET.get('msg', None)
        
        if msg == "Unauthorized":
            logout(request) 
            
        print("in request", request.session.get('roleid'), request.session.get('department'), request.session.get('is_active'))
            
        if request.session.get('roleid') == 2 and request.session.get('department') == 1:
            return redirect("/complaints")
        elif request.session.get('roleid') == 2 and request.session.get('department') == 2:
            return redirect("roaster_list") 
        
        if request.session.get('is_active'):
            return redirect("/home")
        
        msg = request.GET.get('msg', None)
        return render(request,"login.html",{
            'msg': msg, 
            'site_key': RECAPTCHA_SITE_KEY,
            "firebase_config": settings.FIREBASE_CONFIG, 
            'firebase_vapid_key': settings.FIREBASE_VAPID_KEY, 
            'cache_buster': int(time.time())})
    
    def post(self, request):
        username = request.POST.get('username')
        pswd = request.POST.get('password')
        enc_pswd = str_encrypt(str(pswd))
        pswd = enc_pswd

        try:
            # Get reCAPTCHA response from form
            recaptcha_response = request.POST.get('g-recaptcha-response')

            # Verify reCAPTCHA v3 response with Google
            recaptcha_verify_url = "https://www.google.com/recaptcha/api/siteverify"
            recaptcha_data = {
                'secret': RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            recaptcha_result = requests.post(recaptcha_verify_url, data=recaptcha_data).json()

            # Check reCAPTCHA success and score (Google recommends 0.5+)
            if not recaptcha_result.get("success") or recaptcha_result.get("score", 0) < 0.5:
                return render(request, "index.html", {"message": "reCAPTCHA failed. Please try again.", "status": False, "site_key": RECAPTCHA_SITE_KEY, "firebase_config": settings.FIREBASE_CONFIG, })
            
            if pd.isnull(username) or username == '' or username is None:
                return render(request,"login.html",{'message': 'Username should not be empty..!', "status": False, 'site_key': RECAPTCHA_SITE_KEY, "firebase_config": settings.FIREBASE_CONFIG, })
            if pd.isnull(pswd) or pswd == '' or pswd is None:
                return render(request,"login.html",{'message': 'Password should not be empty..!', "status": False, 'site_key': RECAPTCHA_SITE_KEY, "firebase_config": settings.FIREBASE_CONFIG, })
            
            if username is not None and pswd is not None:
                user_dtls = MstUserLogins.objects.filter(loginname=username, securepassword=pswd,status_flag=1)

                if len(user_dtls) > 0:
                    request.session['loginid'] = user_dtls[0].id
                    request.session['loginname'] = user_dtls[0].loginname
                    request.session['roleid'] = user_dtls[0].roleid.id if user_dtls[0].roleid else None
                    request.session['department'] = user_dtls[0].department.id if user_dtls[0].department else None
                    request.session['is_active'] = True
                    request.session['loggedin_user_name'] = user_dtls[0].name
                    request.session['loggedin_user_email'] = user_dtls[0].email
                    log_user_activity(request, "Login", f"User '{username}' logged in successfully")
                    fcm_token = request.POST.get("fcm_token")
                    print("fcm_token-------------", fcm_token)
                    if fcm_token:
                        UserDeviceToken.objects.update_or_create(
                            user_email=user_dtls[0].email,
                            defaults={
                                "device_token":fcm_token,
                                "updated_on": timezone.now(),
                                "updated_by": user_dtls[0].id,
                                "status_flag": 1
                            }
                        )
                    if user_dtls[0].roleid.id == 2:
                        return redirect("/complaints")
                    elif user_dtls[0].roleid.id != 1 and user_dtls[0].department.id == 2:
                        return redirect("roaster_list")
                    return redirect("/home")
                else:
                    return render(request,"login.html",{"message": "Incorrect Password!!", "status": False, 'site_key': RECAPTCHA_SITE_KEY, "firebase_config": settings.FIREBASE_CONFIG, })
            else:
                return render(request,"login.html",{"message": "Please provide both username and password", "status": False, 'site_key': RECAPTCHA_SITE_KEY, "firebase_config": settings.FIREBASE_CONFIG, })
        except Exception as e:
            return render(request,"login.html",{"message": "Please provide both username and password ({e})", "status": False, 'site_key': RECAPTCHA_SITE_KEY, "firebase_config": settings.FIREBASE_CONFIG, })

class PlatformLogoutView(View):
    def post(self, request):
        log_user_activity(request, "Logout", f"User '{request.session.get('loginname')}' logged out successfully")
        user = MstUserLogins.objects.filter(id=request.session.get('loginid')).first()
        UserDeviceToken.objects.filter(user_email=user.email).update(status_flag=0)
        logout(request)
        return redirect(reverse('login'))
    

class Dashboard(TemplateView):
    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        try:
            # Total players
            total_players = Players.objects.filter(status_flag=1).count()

            # Active players (assuming status_flag=1 is active)
            active_players = Players.objects.filter(status="ACTIVE", status_flag=1).count()

            # Pending complaints (assuming status='Pending')
            pending_complaints = PlayerComplaint.objects.filter(status__in=['OPEN', 'IN_PROGRESS'], status_flag=1).count()

            # Total announcements
            total_announcements = Announcements.objects.count()

            players_list = Players.objects.filter(
                status_flag=1
            ).prefetch_related(
                Prefetch(
                    'playertransportationdetails_set',
                    queryset=PlayerTransportationDetails.objects.filter(status_flag=1).order_by('-created_on'),
                    to_attr='all_transports'
                )
            ).select_related('countryid').order_by('-created_on')
            
            paginator = Paginator(players_list, per_page)
            page_number = request.GET.get('page', 1)
            players_page = paginator.get_page(page_number)

            players_with_transport = []
            for player in players_page:
                # Find the latest non-scheduled transport status
                transportation_status = "Not Set"
                
                if player.all_transports:
                    # Iterate through transports to find the first non-scheduled one
                    for transport in player.all_transports:
                        if transport.entry_status != PlayerTransportationDetails.ENTRY_SCHEDULED:
                            transportation_status = transport.player_status_display
                            break
                    else:
                        transportation_status = ""
                
                players_with_transport.append({
                    'player': player,
                    'transportation_status': transportation_status
                })

            context = {
                "total_players": total_players,
                "active_players": active_players,
                "pending_complaints": pending_complaints,
                "total_announcements": total_announcements,
                "players_with_transport": players_with_transport,
                "players_page": players_page,
            }

            return render(request, self.template_name, context)

        except Exception as e:
            return render(request, self.template_name, {
                "message": f"No data available ({e})",
                "status": True
            })
            
            
     
class PlayerView(View):
    template_name = "players.html"

    def get(self, request):
        """
        Render player management page with countries list for dropdown.
        """
        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        
        return render(request, self.template_name, {"countries": countries, "MstUserLogins": MstUserLogins})

    def post(self, request):
        """
        Handle AJAX requests:
        - If 'action' == 'fetch' → return paginated players
        - If 'action' == 'add' → create new player
        - If 'action' == 'edit' → update existing player
        """
        action = request.POST.get("action")
        print("action------------------", action)

        if action == "fetch":
            return self.fetch_players(request)
        elif action == "add":
            return self.add_player(request)
        elif action == "edit":
            return self.edit_player(request)
        elif action == "get-player-details":
            return self.get_player_details(request)
        elif action == "delete":                   
            return self.delete_player(request)
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    def fetch_players(self, request):
    
        page = int(request.POST.get("page", 1))

        players = Players.objects.filter(status_flag=1).prefetch_related(
            Prefetch(
                'playertransportationdetails_set',
                queryset=PlayerTransportationDetails.objects.filter(status_flag=1).order_by('-created_on'),
                to_attr='all_transports'
            )
        ).order_by("-id")

        paginator = Paginator(players, per_page)
        current_page = paginator.get_page(page)

        player_data = []
        for player in current_page:
            transportation_status = ""

            if player.all_transports:
                for transport in player.all_transports:
                    if transport.entry_status != PlayerTransportationDetails.ENTRY_SCHEDULED:
                        transportation_status = transport.player_status_display
                        break

            player_data.append({
                "id": player.id,
                "image_url": player.image.url if player.image else "",
                "name": f"{player.name}",
                "age": getattr(player, "age", None),
                "gender": getattr(player, "gender", None),
                "country": player.countryid.country_name if player.countryid else "",
                "email": player.email,
                "status": player.get_status_display() if player.status else "",
                "transportation_status": transportation_status,
            })

        pagination = {
            "current_page": current_page.number,
            "total_pages": paginator.num_pages,
            "has_next": current_page.has_next(),
            "has_prev": current_page.has_previous(),
            "page_list": list(paginator.get_elided_page_range(number=current_page.number)),
            "per_page": per_page,
        }

        return JsonResponse({"data": player_data, "pagination": pagination})

    def add_player(self, request):
        """
        Add a new player record.
        """
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            age = request.POST.get("age")
            gender = request.POST.get("gender")
            fide_id = request.POST.get("fideId")
            country_id = request.POST.get("country")
            fide_record = FideIDMst.objects.filter(fide_id=fide_id, status_flag=1)
            if not fide_record:
                return JsonResponse({"success": False, "error": "Invalid FIDE ID"})
            
            if Players.objects.filter(fide_id=fide_id).exists():
                return JsonResponse({"success": False, "error": "This FIDE ID is already registered."})

            player = Players.objects.create(
                name=name,
                email=email,
                fide_id=fide_id,
                age=age,
                gender=gender,
                created_by=request.session.get("loginid"),
                created_on=timezone.now(),
                status_flag=1,
                countryid_id=country_id,
                is_self_registered=False
            )
            # PlayerTransportationDetails.objects.create(
            #     playerId=player,
            #     status_flag=1,
            #     entry_status=PlayerTransportationDetails.ENTRY_ARRIVED_AIRPORT,
            # )
            log_user_activity(request, "Add Player", f"Player '{name}' added successfully")

            return JsonResponse({"success": True, "message": "Player added successfully"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def edit_player(self, request):
        """
        Update an existing player.
        """
        try:
            player_id = request.POST.get("id")
            player = get_object_or_404(Players, id=player_id)
            country = CountryMst.objects.get(country_id=request.POST.get("country"), status_flag=1)

            player.name = request.POST.get("name")
            player.email = request.POST.get("email")
            player.gender = request.POST.get("gender")
            player.countryid_id = country
            player.age = request.POST.get("age")
            player.fide_id = request.POST.get("fideId")
            player.updated_on = timezone.now()
            player.updated_by = request.session.get("loginid")
            player.status = request.POST.get("status")
            player.save()
            log_user_activity(request, "Update Player", f"Player '{player.name}' updated successfully")

            return JsonResponse({"success": True, "message": "Player updated successfully"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
        
    def get_player_details(self, request):
        """
        Fetch details of a specific player for editing.
        """
        player_id = request.POST.get("playerId")
        try:
            player = Players.objects.get(id=player_id, status_flag=1)
            data = {
                "id": player.id,
                "name": player.name,
                "email": player.email,
                "age": player.age,
                "gender": player.gender,
                "country": player.countryid_id,
                "fideId": player.fide_id,
                "status": player.status
            }
            log_user_activity(request, "Get Player Details", f"Player '{player.name}' details fetched successfully")
            return JsonResponse({"success": True, "data": data})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "error": "Player not found"})

    def delete_player(self, request):
        """
        Soft delete (set status_flag = 0)
        """
        player_id = request.POST.get("id")
        try:
            player = Players.objects.get(id=player_id)
            player.status_flag = 0
            player.updated_on = timezone.now()
            player.updated_by = request.session.get("loginid")
            player.deactivated_by = request.session.get("loginid")
            player.deactivated_on = timezone.now()
            player.save()
            log_user_activity(request, "Delete Player", f"Player '{player.name}' deleted successfully")
            return JsonResponse({"success": True, "message": "Player deleted successfully"})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "error": "Player not found"})
        

class PlayerTransportStatusView(View):
    def get(self, request, player_id):
        """Get status options for a player"""
        try:
            player = get_object_or_404(Players, id=player_id, status_flag=1)
            
            # Get all status mappings for dropdown
            status_mappings = TransportStatusMapping.objects.filter(status_flag=1).order_by('player_status').values('player_status').distinct()
            print("status_mappings", status_mappings)
            
            status_options = []
            for mapping in status_mappings:
                status_options.append({
                    'player_status': mapping['player_status'],
                })
                
            print("status_options", status_options)
            
            return JsonResponse({
                'player_name': player.name,
                'status_options': status_options
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def post(self, request, player_id):
        """Create transport entry with selected status"""
        try:
            player = get_object_or_404(Players, id=player_id, status_flag=1)
            status_type = request.POST.get('status_type')
            
            if not status_type:
                return JsonResponse({'success': False, 'error': 'Status type is required'})
            
            # Verify the status mapping exists
            mapping = TransportStatusMapping.objects.filter(
                player_status=status_type,
                status_flag=1
            ).first()
            
            if not mapping:
                return JsonResponse({'success': False, 'error': 'Invalid status mapping'})
            
            # Create a new transport entry without roaster
            PlayerTransportationDetails.objects.create(
                playerId=player,
                entry_status=mapping.status_type,
                created_by=request.session.get('loginid'),
                status_flag=1,
                details=mapping.id
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Transport status updated: {mapping.get_status_type_display()} - {mapping.player_status}',
                'player_status': mapping.player_status
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})     
        
                        
class PlayerProfile(View):
    template_name = "player-profile.html"

    def get(self, request, player_id):
        player = get_object_or_404(Players, id=player_id, status_flag=1)
        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        TransportationTypes = TransportationType.objects.filter(status_flag=1).order_by("Name")
        player_documents = PlayerDocument.objects.filter(player=player, status_flag=1)
        
        # Get all transportation details for this player with roaster info
        transportation_details = PlayerTransportationDetails.objects.filter(
            playerId=player, 
            status_flag=1
        ).select_related(
            'roasterId', 
        ).order_by('-created_on')
        
        # Get the latest roaster assignment
        latest_transport = transportation_details.first()
        current_roaster = latest_transport.roasterId if latest_transport else None
        
        # Get all status updates for the current roaster
        roaster_status_updates = []
        if current_roaster:
            roaster_status_updates = PlayerTransportationDetails.objects.filter(
                roasterId=current_roaster,
                playerId=player,
                status_flag=1
            ).order_by('-created_on')[:0]
        
        # Get current transport status for the dropdown
        current_transport_status = latest_transport.entry_status if latest_transport else None
        
        return render(request, self.template_name, {
            "player": player, 
            "countries": countries, 
            "TransportationTypes": TransportationTypes,
            "player_documents": player_documents,
            "transportation_details": transportation_details,
            "current_roaster": current_roaster,
            "roaster_status_updates": roaster_status_updates,
            "current_transport_status": current_transport_status,
            "transport_status_choices": PlayerTransportationDetails.ENTRY_STATUS_CHOICES,
        })
    
class UpdatePlayerProfile(View):
    def post(self, request):
        player_id = request.POST.get("player_id")
        print("request post update profile", request.POST)
        print("request.FILES", request.FILES)
        player = get_object_or_404(Players, id=player_id, status_flag=1)

        fide_id = request.POST.get("fide_id")
        
        # Check if FIDE ID exists in FideIDMst
        if not FideIDMst.objects.filter(fide_id=fide_id).exists():
            return JsonResponse({"success": False, "error": "FIDE ID does not exist."})
        
        # Check if FIDE ID is already assigned to another player
        if Players.objects.filter(fide_id=fide_id).exclude(id=player_id).exists():
            return JsonResponse({"success": False, "error": "This FIDE ID is already registered with another player."})
        
        age = request.POST.get("age")
        if age == '':
            age = None
        else:
            try:
                age = int(age) if age else None
            except (ValueError, TypeError):
                age = None

        # Update player details
        player.name = request.POST.get("name")
        player.fide_id = fide_id
        player.age = age
        player.gender = request.POST.get("gender")
        player.email = request.POST.get("email")
        player.status = request.POST.get("status")
        player.countryid_id = request.POST.get("country")
        player.details = request.POST.get("food_allergies", player.details)
        player.room_cleaning_preference = request.POST.get("room_cleaning_preference", player.room_cleaning_preference)
        player.accompanying_persons = request.POST.get("accompanying_persons", player.accompanying_persons)

        # Handle profile picture upload
        if "profile_pic" in request.FILES: 
            player.image = request.FILES["profile_pic"]

        # Handle multiple documents upload - UPDATED
        if "documents" in request.FILES:
            documents = request.FILES.getlist("documents")  # Get all files
            fide_id = player.fide_id
            
            for document in documents:
                original_name = document.name
                new_filename = f"{fide_id}_{original_name}"
                
                # Create PlayerDocument record
                player_doc = PlayerDocument(
                    player=player,
                    reg_document=document,
                    original_filename=original_name,
                    file_size=document.size,
                    document_type='IDENTIFICATION'
                )
                # Rename the file
                player_doc.reg_document.name = new_filename
                player_doc.save()

        # Set update timestamp and user
        player.updated_on = timezone.now()
        player.updated_by = request.session.get("loginid")
        player.save()

        data = {"success": True}
        if player.image:
            data["image_url"] = player.image.url
        
        # Get documents for response
        player_documents = PlayerDocument.objects.filter(player=player, status_flag=1)
        if player_documents.exists():
            data["documents"] = [doc.original_filename for doc in player_documents]

        log_user_activity(request, "Update Player Profile", f"Player '{player.name}' profile updated successfully")
        return JsonResponse(data)
    

class DeletePlayerDocument(View):
    def post(self, request):
        document_id = request.POST.get("document_id")
        try:
            document = PlayerDocument.objects.get(id=document_id, status_flag=1)
            document.status_flag = 0  # Soft delete
            document.save()
            
            return JsonResponse({"success": True, "message": "Document deleted successfully"})
        except PlayerDocument.DoesNotExist:
            return JsonResponse({"success": False, "error": "Document not found"})
    
class PlayerTransportView(View):
    def get(self, request, player_id):
        try:
            player = get_object_or_404(Players, id=player_id, status_flag=1)

            transport_details = PlayerTransportationDetails.objects.filter(
                playerId=player
            ).select_related('roasterId').order_by('created_on')

            transport_data = []
            for transport in transport_details:
                username = "logistics team"
                if transport.created_by:
                    user = MstUserLogins.objects.filter(id=transport.created_by).first()
                    if user:
                        username = user.name

                transport_type = ""
                vehicle_no = ""
                driver_name = ""
                driver_phone = ""
                pickup = ""
                dropoff = ""
                travel_date = ""

                # Get location and vehicle info from Roaster if available
                if transport.roasterId:
                    roaster = transport.roasterId
                    transport_type = roaster.vechicle_type or ""
                    vehicle_no = roaster.vechicle_no or ""
                    driver_name = roaster.driver_name or ""
                    driver_phone = f"+{roaster.mobile_no}" if roaster.mobile_no else ""
                    
                    # Get locations from Roaster
                    if roaster.pickup_location:
                        pickup = roaster.pickup_location_custom if roaster.pickup_location == Roaster.LOCATION_OTHER else roaster.get_pickup_location_display()
                    
                    if roaster.drop_location:
                        dropoff = roaster.drop_location_custom if roaster.drop_location == Roaster.LOCATION_OTHER else roaster.get_drop_location_display()
                    
                    travel_date = roaster.travel_date.strftime("%d %b %Y at %I:%M %p") if roaster.travel_date else ""

                # Handle status text based on entry status
                if transport.entry_status == PlayerTransportationDetails.ENTRY_SCHEDULED:
                    if transport.roasterId:
                        status_text = f"Transport scheduled for {travel_date} in {transport_type} no. {vehicle_no} from {pickup} to {dropoff}<br>Driver: {driver_name} | Phone: {driver_phone}<br>Updated at: {transport.created_on.strftime('%d %b %Y at %I:%M %p')}"
                    else:
                        status_text = f"Transport scheduled<br>Updated at: {transport.created_on.strftime('%d %b %Y at %I:%M %p')}"
                else:
                    # Use the player_status_display property from the model
                    status_display = transport.player_status_display
                    status_text = f"Your status was marked as {status_display} by {username} from the logistics team.<br>Updated at: {transport.created_on.strftime('%d %b %Y at %I:%M %p')}"

                transport_data.append({
                    'id': transport.id,
                    'roaster_id': transport.roasterId.id if transport.roasterId else None,
                    'player_name': player.name,
                    'entry_status': transport.entry_status,
                    'status_display': status_text,
                    'pickup_location': pickup,
                    'drop_location': dropoff,
                    'travel_date': travel_date,
                    'created_on': transport.created_on.strftime("%d %b %Y at %I:%M %p"),
                    'created_on_timestamp': transport.created_on.timestamp(),
                    'vehicle_type': transport_type,
                    'vehicle_number': vehicle_no,
                    'driver_name': driver_name,
                    'driver_phone': driver_phone,
                })
                
            print("transport_data", transport_data)

            return JsonResponse(transport_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)



class ComplaintListView(View):
    """Displays all complaints and their conversation threads with search and pagination"""

    def get(self, request):
        search_query = request.GET.get("q", "")
        selected_department = request.GET.get("department", "")
        status_filter = request.GET.get("status", "")
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        export = request.GET.get("export", "")

        role_id = request.session.get("roleid")
        user_dept_id = request.session.get("department")

        log_user_activity(request, "View Complaints", "User viewed complaints list")

        # Base queryset
        complaints_qs = PlayerComplaint.objects.select_related("player", "department").prefetch_related(
            Prefetch(
                "conversations",
                queryset=PlayerComplaintConversation.objects.select_related("sender_player", "sender_user").order_by("-created_on")
            )
        ).order_by("-created_on")

        # Apply department filter based on role
        if role_id == 2 and user_dept_id == 1:
            if user_dept_id in [1]:
                complaints_qs = complaints_qs.filter(department_id__in=[1])
                if not selected_department:
                    selected_department = "1"
            else:
                complaints_qs = complaints_qs.filter(department_id=user_dept_id)
                selected_department = user_dept_id
        elif role_id == 2 and user_dept_id == 2:
            complaints_qs = complaints_qs.filter(department_id=2)
            selected_department = "2"
        elif role_id == 1:
            if selected_department:
                complaints_qs = complaints_qs.filter(department_id=selected_department)

        # Apply status filter
        if status_filter:
            complaints_qs = complaints_qs.filter(status=status_filter)

        # Apply date range filter
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                complaints_qs = complaints_qs.filter(created_on__date__gte=start_date_obj)
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                complaints_qs = complaints_qs.filter(created_on__date__lte=end_date_obj)
            except ValueError:
                pass

        # Apply search filter
        if search_query:
            complaints_qs = complaints_qs.filter(
                models.Q(player__name__icontains=search_query) |
                models.Q(description__icontains=search_query)
            )

        # Handle export functionality
        if export and role_id == 1:
            return self.export_complaints(complaints_qs)

        paginator = Paginator(complaints_qs, per_page)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        departments = Department.objects.filter(status_flag=1).order_by("name")

        return render(request, "complaints.html", {
            "complaints": page_obj,
            "search_query": search_query,
            "page_obj": page_obj,
            "departments": departments,
            "selected_department": str(selected_department),
            "role_id": role_id,
            "status_filter": status_filter,
            "start_date": start_date,
            "end_date": end_date,
            "status_choices": PlayerComplaint.STATUS_CHOICES,
        })

    def export_complaints(self, complaints_qs):
        """Export complaints to Excel with formatted output matching HTML display"""
        try:
            # Prepare data for export
            export_data = []
            for complaint in complaints_qs:
                # Get all conversations formatted like in HTML
                conversations_text = ""
                if complaint.conversations.all():
                    for convo in complaint.conversations.all():
                        # Format exactly like in HTML template
                        sender_name = ""
                        if convo.sender_player:
                            sender_name = convo.sender_player.name
                        elif convo.sender_user:
                            sender_name = convo.sender_user.name
                        else:
                            sender_name = "Unknown"

                        conversation_date = convo.created_on.strftime("%b %d, %H:%M")
                        conversations_text += f"{sender_name} ({conversation_date})\n{convo.message}\n\n"
                else:
                    conversations_text = "No conversations yet"

                export_data.append({
                    'complaint_id': f"C{complaint.id}",
                    'player_name': complaint.player.name,
                    'department': complaint.department.name if complaint.department else "N/A",
                    'description': complaint.description,
                    'status': complaint.get_status_display(),
                    'created_date': complaint.created_on.strftime("%d %b %Y"),
                    'created_time': complaint.created_on.strftime("%I:%M %p"),
                    'conversations': conversations_text.strip(),
                    'conversation_count': complaint.conversations.count(),
                })

            # Convert to DataFrame
            df = pd.DataFrame(export_data)
            
            # Rename columns for Excel display to match HTML
            if not df.empty:
                df.rename(
                    columns={
                        'complaint_id': 'Complaint ID',
                        'player_name': 'Player Name',
                        'department': 'Department',
                        'description': 'Description',
                        'status': 'Status',
                        'created_date': 'Created Date',
                        'created_time': 'Created Time',
                        'conversations': 'Conversations',
                        'conversation_count': 'Total Conversations',
                    },
                    inplace=True
                )

            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Write data starting from row 2 to leave space for title
                df.to_excel(writer, sheet_name="Complaints Report", startrow=2, index=False)

                workbook = writer.book
                worksheet = writer.sheets["Complaints Report"]

                # Add title
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 16,
                    'align': 'center',
                })

                date_format = workbook.add_format({
                    'bold': False,
                    'font_size': 12,
                    'align': 'center',
                })

                # Write title
                worksheet.merge_range('A1:H1', 'COMPLAINTS REPORT', title_format)
                worksheet.merge_range('A2:H2', f'Generated on: {datetime.now().strftime("%d %b %Y at %I:%M %p")}', date_format)

                # Add header formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#271f64',
                    'font_color': 'white',
                    'border': 1,
                    'align': 'center',
                })

                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(2, col_num, value, header_format)

                # Add data formatting
                data_format = workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                })

                # Apply data format to all data cells
                for row_num in range(3, len(df) + 3):
                    for col_num in range(len(df.columns)):
                        worksheet.write(row_num, col_num, df.iat[row_num-3, col_num], data_format)

                

                # Set column widths
                column_widths = {
                    'Complaint ID': 12,
                    'Player Name': 20,
                    'Department': 15,
                    'Description': 40,
                    'Status': 15,
                    'Created Date': 12,
                    'Created Time': 10,
                    'Conversations': 50,  # Wider for conversation text
                    'Total Conversations': 12,
                }

                # Apply column widths
                for col_num, column_name in enumerate(df.columns):
                    width = column_widths.get(column_name, 15)
                    worksheet.set_column(col_num, col_num, width)

                # Add autofilter
                worksheet.autofilter(2, 0, len(df) + 2, len(df.columns) - 1)

                # Freeze header row and title
                worksheet.freeze_panes(3, 0)

            # Prepare response
            output.seek(0)
            filename = f"Complaints_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            response = HttpResponse(
                output,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            log_user_activity(self.request, "Export Complaints", "Complaints data exported to Excel")
            return response

        except Exception as e:
            return HttpResponse(f"Error exporting data: {str(e)}", status=500)


class ComplaintUpdateView(View):
    """Handles AJAX updates — status change, department change or adding remarks"""

    def post(self, request, complaint_id):
        complaint = get_object_or_404(PlayerComplaint, id=complaint_id)
        new_status = request.POST.get("status")
        new_department = request.POST.get("department")
        message = request.POST.get("message")
        print("new_status", new_status, "new_department", new_department, "message", message)

        notification_needed = False
        notification_message = ""

        if new_status:
            complaint.status = new_status
            complaint.save()
            log_user_activity(request, "Update Complaint Status", f"Complaint ID(#C{complaint_id}) status updated to {new_status}")
            notification_needed = True
            notification_message += f"Status updated to {new_status}. "

        if new_department:
            try:
                department = Department.objects.get(id=new_department)
                complaint.department = department
                complaint.save()
                log_user_activity(request, "Update Complaint Department", f"Complaint ID(#C{complaint_id}) department updated to {department.name}")
                notification_needed = True
                notification_message += f"Department changed to {department.name}. "
            except Department.DoesNotExist:
                return JsonResponse({"success": False, "message": "Invalid department."})

        if message:
            sender = MstUserLogins.objects.get(id=request.session.get("loginid"), status_flag=1)
            PlayerComplaintConversation.objects.create(complaint=complaint, sender_user=sender, message=message)
            log_user_activity(request, "Add Remark", f"Complaint ID({complaint_id}) remark added")
            notification_needed = True
            notification_message += "New remark added. "
            self._send_complaint_reply_email(complaint, message, sender)

        complaint.updated_by = request.session.get("loginid")
        complaint.updated_on = timezone.now()
        complaint.save()

        # --- SEND PUSH NOTIFICATION ---
        if notification_needed:
            try:
                # Get all device tokens for the player
                device_tokens = UserDeviceToken.objects.filter(
                    user_email=complaint.player.email,
                    status_flag=1
                ).values_list("device_token", flat=True)

                title = f"Complaint #{complaint.id} Updated"
                body = notification_message.strip()

                for token in device_tokens:
                    if token:
                        try:
                            send_push_notification(request, token, title, body)
                            print(f"Push sent to token: {token}")
                        except Exception as e:
                            print(f"Failed to send push to token {token}: {str(e)}")
            except Exception as e:
                print("Error sending push notifications:", e)

        return JsonResponse({"success": True, "message": "Complaint updated successfully."})

    def _send_complaint_reply_email(self, complaint, message, sender):
        """Send email notification to player about complaint reply"""
        try:
            player = complaint.player
            context = {
                'player_name': player.name,
                'complaint_id': complaint.id,
                'admin_message': message,
                'admin_name': sender.name if hasattr(sender, 'name') else "Admin Team",
                'complaint_status': complaint.status,
                'department_name': complaint.department.name,
                'reply_date': timezone.now().strftime("%B %d, %Y at %I:%M %p"),
                'complaint_description': complaint.description[:100] + "..." if len(complaint.description) > 100 else complaint.description
            }

            html_message = render_to_string('complaint_reply_to_player.html', context)
            subject = f"Update on Your Complaint #C{complaint.id} - FWC 2025"

            email_log = EmailLog.objects.create(
                email_type='COMPLAINT_REPLY_TO_PLAYER',
                subject=subject,
                recipient_email=player.email,
                status='PENDING',
                html_content=html_message,
                text_content=f"Update on your complaint #{complaint.id}",
            )

            send_mail(
                subject=subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[player.email],
                html_message=html_message,
                fail_silently=False,
            )

            email_log.status = 'SENT'
            email_log.save()

        except Exception as e:
            print(f"Failed to send complaint reply email: {str(e)}")

    

class AnnouncementListView(View):
    def get(self, request):
        # Your existing GET method code remains the same
        search_query = request.GET.get("q", "")

        announcements = Announcements.objects.select_related("created_by").prefetch_related(
            'recipients__player'
        ).all().order_by("-created_on")
        
        if search_query:
            announcements = announcements.filter(title__icontains=search_query)

        paginator = Paginator(announcements, per_page) 
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        players = Players.objects.filter(status_flag=1).order_by("name")

        return render(request, "announcements.html", {
            "page_obj": page_obj,
            "players": players,
            "search_query": search_query
        })

    def post(self, request):
        """Create new announcement and assign recipients"""
        title = request.POST.get("title")
        details = request.POST.get("details")
        audience_ids = request.POST.get("selected_players", "").split(",") if request.POST.get("selected_players") else []
        current_user = request.session.get("loginid")
        print("title", title, "details", details, "audience_ids", audience_ids, "current_user", current_user)   
        logged_user=MstUserLogins.objects.get(id=current_user)
        
        if not audience_ids:
            return JsonResponse({"success": False, "message": "Please select at least one player."})
        audience_ids = [pid for pid in audience_ids if pid]

        announcement = Announcements.objects.create(
            title=title,
            details=details,
            created_by=logged_user,
            created_on=timezone.now()
        )
        
        recipients = Players.objects.filter(id__in=audience_ids)

        AnnouncementRecipients.objects.bulk_create([
            AnnouncementRecipients(announcement=announcement, player=p, sent_on=timezone.now())
            for p in recipients
        ])
        log_user_activity(request, "Create Announcement", f"Announcement '{title}' created successfully")
        
        # Send emails to each recipient
        self._send_announcement_emails(announcement, recipients)
        
        # Send push notifications
        try:
            device_tokens = UserDeviceToken.objects.filter(
                user_email__in=[p.email for p in recipients],
                status_flag=1
            ).values_list("device_token", flat=True)
            print("sending notification for announcement",)

            notification_title = f"New Announcement: {title}"
            notification_body = details[:100] + "..." if len(details) > 100 else details

            for token in device_tokens:
                if token:
                    try:
                        send_push_notification(request, token, notification_title, notification_body)
                        print(f"Push sent to token: {token}")
                    except Exception as e:
                        print(f"Failed to send push to token {token}: {str(e)}")

        except Exception as e:
            print("Error sending push notifications:", e)

        return redirect("announcements")
    
    def _send_announcement_emails(self, announcement, recipients):
        """Send announcement emails to each player individually"""
        for player in recipients:
            try:
                context = {
                    'player_name': player.name,
                    'player_fide_id': player.fide_id,
                    'player_email': player.email,
                    'announcement_date': announcement.created_on.strftime("%B %d, %Y at %I:%M %p"),
                    'announcement_id': announcement.id,
                    'priority': 'Important',
                    'announcement_title': announcement.title,
                    'announcement_details': announcement.details
                }

                html_message = render_to_string('announcement_player_email.html', context)
                subject = f"New Announcement: {announcement.title} - FWC 2025"

                email_log = EmailLog.objects.create(
                    email_type='ANNOUNCEMENT',
                    subject=subject,
                    recipient_email=player.email,
                    status='PENDING',
                    html_content=html_message,
                    text_content=f"New announcement: {announcement.title}",
                )

                send_mail(
                    subject=subject,
                    message="",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[player.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                email_log.status = 'SENT'
                email_log.save()
                print(f"Announcement email sent to {player.email}")

            except Exception as e:
                print(f"Failed to send announcement email to {player.email}: {str(e)}")

    
    
class ManageUsersView(View):
    template_name = "users.html"

    def get(self, request):
        users = MstUserLogins.objects.filter(status_flag=1).order_by("-created_on")
        roles = MstRole.objects.filter(status_flag=1)  # Active roles
        departments = Department.objects.filter(status_flag=1)  # Active departments
        
        paginator = Paginator(users, per_page) 
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        context = {
            "page_obj": page_obj,
            "roles": roles,
            "departments": departments,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        name = request.POST.get("name")
        loginname = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirmPassword")
        role_id = int(request.POST.get("role"))
        department_id = request.POST.get("department")
        print("request.POST", request.POST)
        
        existing_user = MstUserLogins.objects.filter(
            Q(loginname__iexact=loginname) | Q(email__iexact=email)
        ).first()

        if existing_user:
            if existing_user.loginname.lower() == loginname.lower():
                return JsonResponse({"success": False, "message": f"Username '{loginname}' already exists."})
            elif existing_user.email.lower() == email.lower():
                return JsonResponse({"success": False, "message": f"Email '{email}' is already registered."})

        # Validate password
        if password != confirm_password:
            return JsonResponse({"success": False, "message": "Passwords do not match."})
        

        # Fetch role and department objects
        department, new_role_id = None, None
        if department_id:
            department = Department.objects.get(id=department_id)
            
        role = MstRole.objects.get(id=role_id)  
        print("role", role, "department", department, "new_role_id", new_role_id)
        
        enc_pswd = str_encrypt(str(password))
        pswd = enc_pswd

        # Create user
        user = MstUserLogins.objects.create(
            name=name,
            loginname=loginname,
            securepassword=pswd,
            email=email,
            mobilenumber=phone,
            roleid=role,
            department=department,
        )
        log_user_activity(request, "Add User", f"New user '{loginname}' created")
        
        return JsonResponse({"success": True, "message": "User added successfully."})
    
        
class DeleteUserView(View):
    def post(self, request, user_id):
        user = get_object_or_404(MstUserLogins, id=user_id)
        user.status_flag = 0
        user.updated_on = timezone.now()
        user.updated_by = request.session.get("loginid")
        user.deactivated_by = request.session.get("loginid")
        user.deactivated_on = timezone.now()
        user.save()
        log_user_activity(request, "Delete User", f"User ID({user_id}) - {user.loginname} deleted")
        return JsonResponse({"success": True, "message": "User deleted successfully."})


class EditUserView(View):
    def get(self, request, user_id):
        """Return user data for editing"""
        user = get_object_or_404(MstUserLogins, pk=user_id)
        data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "username": user.loginname,
            "mobilenumber": user.mobilenumber,
            "department": user.department.id if user.department else None,
            "roleid": user.roleid.id if user.roleid else None,
        }
        log_user_activity(request, "Fetch Data To Edit User", f"User ID({user_id}) - {user.name} edited")
        return JsonResponse({"success": True, "data": data})
    
    def post(self, request, user_id):
        print("rest", request.POST)
        user = get_object_or_404(MstUserLogins, id=user_id)
        role_id = request.POST.get("edit_role")
        department_id = request.POST.get("edit_department")
        role = MstRole.objects.get(id=role_id)
        department = None
        if department_id: 
            department = Department.objects.get(id=department_id)
        
        user.name = request.POST.get("edit_name")
        user.loginname = request.POST.get("edit_username")
        user.email = request.POST.get("edit_email")
        user.mobilenumber = request.POST.get("edit_phone")
        user.roleid = role
        user.department = department
        user.updated_on = timezone.now()
        user.updated_by = request.session.get("loginid")
        user.save()
        log_user_activity(request, "Update User", f"User ID({user_id}) - {user.name} updated")
        return JsonResponse({"success": True, "message": "User updated successfully."})
    
    
class ChangeUserPasswordView(View):
    def post(self, request):
        user_id = request.POST.get("userId")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not new_password or not confirm_password:
            return JsonResponse({"success": False, "message": "Please fill in all fields."})

        if new_password != confirm_password:
            return JsonResponse({"success": False, "message": "Passwords do not match."})

        try:
            user = MstUserLogins.objects.get(id=user_id, status_flag=1)
            enc_pswd = str_encrypt(str(new_password))
            user.securepassword = enc_pswd
            user.save()
            log_user_activity(request, "Change Password", f"User ID({user_id}) - {user.loginname} password changed")
            return JsonResponse({"success": True, "message": "Password updated successfully."})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "message": "User not found."})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Error: {str(e)}"})
        
        
        
class UserActivityLogView(TemplateView):
    template_name = "activity_log.html"

    def get(self, request):
        page = request.GET.get("page", 1)
        search = request.GET.get("search", "")
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        sort_by = request.GET.get("sort_by", "created_on")
        sort_order = request.GET.get("sort_order", "desc")

        logs = UserActivityLog.objects.select_related("user", "user__roleid").all()
            
        # Apply search filter
        if search:
            logs = logs.filter(
                Q(user__loginname__icontains=search) |
                Q(user__name__icontains=search) |
                Q(user__roleid__role_name__icontains=search) |
                Q(action__icontains=search) |
                Q(description__icontains=search)
            )

        # Apply date filter
        if start_date:
            logs = logs.filter(created_on__gte=start_date)
        if end_date:
            # Add one day to include the entire end date
            import datetime
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            end_date_plus_one = end_date_obj + datetime.timedelta(days=1)
            logs = logs.filter(created_on__lt=end_date_plus_one)

        # Apply sorting
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        logs = logs.order_by(sort_by)

        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)

        return render(request, self.template_name, {
            "page_obj": page_obj,
            "search": search,
            "start_date": start_date,
            "end_date": end_date,
            "sort_by": sort_by.lstrip('-'),  # Remove the '-' for display
            "sort_order": sort_order,
        })


class PlayerRegistrationView(FormView):
    template_name = "player_registration.html"
    form_class = PlayerRegistrationForm
    success_url = reverse_lazy('player_registration')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        # Save the form data
        try:
            player = form.save()
            messages.success(self.request, 'Registration submitted successfully!')
        except Exception as e:
            messages.error(self.request, f'Error submitting registration: {str(e)}')
        return super().form_valid(form)
    
  
  
class RoasterListView(View):
    template_name = "logistics.html"

    def get(self, request):
        search_query = request.GET.get('search', '')
        page_number = request.GET.get('page', 1)

        roasters = Roaster.objects.filter(status_flag=1).order_by('-created_on')
        if search_query:
            roasters = roasters.filter(
                Q(driver_name__icontains=search_query) |
                Q(vechicle_no__icontains=search_query) |
                Q(playertransportationdetails__playerId__name__icontains=search_query)
            ).distinct()

        for r in roasters:
            latest_transport = PlayerTransportationDetails.objects.filter(
                roasterId=r,
                status_flag=1
            ).order_by('-created_on').first()
            
            if latest_transport:
                r.current_entry_status = latest_transport.entry_status
            else:
                r.current_entry_status = "SCHEDULED"

            players_transports = PlayerTransportationDetails.objects.filter(
                roasterId=r,
                status_flag=1
            ).select_related('playerId')
            
            seen = set()
            distinct_players = []
            for p in players_transports:
                if p.playerId.id not in seen:
                    distinct_players.append(p)
                    seen.add(p.playerId.id)
            r.distinct_players = distinct_players

        paginator = Paginator(roasters, per_page)
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'roasters': page_obj.object_list,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)
  
    
    
class RoasterAddView(View):
    template_name = "add-roaster.html"

    def get(self, request):
        players = Players.objects.filter(status_flag=1).order_by("name")
        transportation_types = TransportationType.objects.filter(status_flag=1)
        current_page = request.GET.get('page', 1)
        return render(request, self.template_name, {
            'players': players,
            'transportation_types': transportation_types,
            'location_choices': Roaster.LOCATION_CHOICES,
            'current_page': current_page
        })

    def post(self, request):
        vehicle_type = request.POST.get('vehicleType')
        vehicle_number = request.POST.get('vehicleNumber')
        number_of_seats = request.POST.get('number_of_seats')
        driver_name = request.POST.get('driverName', None)
        mobile_no = request.POST.get('mobile_no', None)
        # transportation_type_id = request.POST.get('transportationTypeId')
        assigned_players = request.POST.getlist('players')
        current_page = request.POST.get('current_page', 1)
        travel_date_str = request.POST.get('travel_date')
        travel_date = datetime.strptime(travel_date_str, "%Y-%m-%d %I:%M %p") if travel_date_str else None
        pickup_location = request.POST.get('pickup_location')
        drop_location = request.POST.get('drop_location')
        pickup_location_custom = request.POST.get('pickup_location_custom', '').strip()
        drop_location_custom = request.POST.get('drop_location_custom', '').strip()

        if pickup_location == Roaster.LOCATION_OTHER and drop_location == Roaster.LOCATION_OTHER:
            messages.error(request, "Cannot create transport from 'Other' to 'Other' location.")
            return redirect(f"{reverse('add_roaster')}?page={current_page}")

        if pickup_location == Roaster.LOCATION_OTHER and not pickup_location_custom:
            messages.error(request, "Please specify the pickup location for 'Other'.")
            return redirect(f"{reverse('add_roaster')}?page={current_page}")

        if drop_location == Roaster.LOCATION_OTHER and not drop_location_custom:
            messages.error(request, "Please specify the drop location for 'Other'.")
            return redirect(f"{reverse('add_roaster')}?page={current_page}")
        
        if mobile_no == '':
            mobile_no = None
        elif mobile_no is not None:
            try:
                mobile_no = int(mobile_no)
            except (ValueError, TypeError):
                mobile_no = None

        roaster = Roaster.objects.create(
            vechicle_type=vehicle_type,
            vechicle_no=vehicle_number,
            number_of_seats=number_of_seats,
            driver_name=driver_name,
            mobile_no=mobile_no,
            # transportationTypeId_id=transportation_type_id,
            pickup_location=pickup_location, 
            pickup_location_custom=pickup_location_custom if pickup_location == Roaster.LOCATION_OTHER else None,
            drop_location=drop_location,   
            drop_location_custom=drop_location_custom if drop_location == Roaster.LOCATION_OTHER else None,   
            travel_date=travel_date,
            status_flag=1,
            created_by=request.session.get('loginid'),
        )

        for player_id in assigned_players:
            player = Players.objects.get(id=player_id)
            PlayerTransportationDetails.objects.create(
                playerId=player,
                roasterId=roaster, 
                entry_status=PlayerTransportationDetails.ENTRY_SCHEDULED,
                created_by=request.session.get('loginid')
            )

        messages.success(request, "Roaster and player travel details added successfully!")
        return redirect(f"{reverse('roaster_list')}?page={current_page}")
    

class RoasterEditView(View):
    template_name = "edit-roaster.html"

    def get(self, request, roaster_id):
        roaster = get_object_or_404(Roaster, id=roaster_id)
        players = Players.objects.filter(status_flag=1).order_by("name")
        current_transport = roaster.playertransportationdetails_set.filter(status_flag=1).first()
        assigned_player_ids = list(roaster.playertransportationdetails_set.filter(
            status_flag=1
        ).values_list('playerId__id', flat=True))
        transportation_types = TransportationType.objects.filter(status_flag=1)
        current_page = request.GET.get('page', 1)

        return render(request, self.template_name, {
            'roaster': roaster,
            'players': players,
            'assigned_player_ids': assigned_player_ids,
            'transportation_types': transportation_types,
            'location_choices': Roaster.LOCATION_CHOICES,
            'current_transport': current_transport,
            'current_page': current_page
        })

    def post(self, request, roaster_id):
        roaster = get_object_or_404(Roaster, id=roaster_id)
        print("reques. post", request.POST)
        vehicle_type = request.POST.get('vehicleType')
        vehicle_number = request.POST.get('vehicleNumber')
        number_of_seats = request.POST.get('number_of_seats')
        driver_name = request.POST.get('driverName')
        mobile_no = request.POST.get('mobile_no')
        assigned_players = request.POST.getlist('players')
        current_page = request.POST.get('current_page', 1)
        travel_date_str = str(request.POST.get('travel_date'))
        travel_date = datetime.strptime(travel_date_str, "%Y-%m-%d %I:%M %p") if travel_date_str else None
        pickup_location = request.POST.get('pickup_location')
        drop_location = request.POST.get('drop_location')
        pickup_location_custom = request.POST.get('pickup_location_custom', '').strip()
        drop_location_custom = request.POST.get('drop_location_custom', '').strip()

        if pickup_location == Roaster.LOCATION_OTHER and drop_location == Roaster.LOCATION_OTHER:
            messages.error(request, "Cannot create transport from 'Other' to 'Other' location.")
            return redirect(f"{reverse('edit_roaster', args=[roaster_id])}?page={current_page}")

        if pickup_location == Roaster.LOCATION_OTHER and not pickup_location_custom:
            messages.error(request, "Please specify the pickup location for 'Other'.")
            return redirect(f"{reverse('edit_roaster', args=[roaster_id])}?page={current_page}")

        if drop_location == Roaster.LOCATION_OTHER and not drop_location_custom:
            messages.error(request, "Please specify the drop location for 'Other'.")
            return redirect(f"{reverse('edit_roaster', args=[roaster_id])}?page={current_page}")
        if mobile_no == '':
            mobile_no = None
        elif mobile_no is not None:
            try:
                mobile_no = int(mobile_no)
            except (ValueError, TypeError):
                mobile_no = None
        

        # Update roaster with mobile number
        roaster.vechicle_type = vehicle_type
        roaster.vechicle_no = vehicle_number
        roaster.number_of_seats = number_of_seats
        roaster.driver_name = driver_name
        roaster.mobile_no = mobile_no
        roaster.pickup_location=pickup_location
        roaster.pickup_location_custom=pickup_location_custom if pickup_location == Roaster.LOCATION_OTHER else None
        roaster.drop_location=drop_location
        roaster.drop_location_custom=drop_location_custom if drop_location == Roaster.LOCATION_OTHER else None
        roaster.travel_date=travel_date
        roaster.updated_by = request.session.get('loginid')
        roaster.updated_on = timezone.now()
        roaster.save()

        # Player management logic
        current_assigned_players = set(roaster.playertransportationdetails_set.filter(
            status_flag=1
        ).values_list('playerId__id', flat=True))
        new_assigned_players = set(int(player_id) for player_id in assigned_players)

        # Remove players
        players_to_remove = current_assigned_players - new_assigned_players
        if players_to_remove:
            PlayerTransportationDetails.objects.filter(
                roasterId=roaster,
                playerId__id__in=players_to_remove,
                status_flag=1
            ).update(
                status_flag=0,
                updated_by=request.session.get('loginid'),
                updated_on=timezone.now()
            )

        players_to_add = new_assigned_players - current_assigned_players
        for player_id in players_to_add:
            player = Players.objects.get(id=player_id)
            PlayerTransportationDetails.objects.create(
                playerId=player,
                roasterId=roaster,
                entry_status=PlayerTransportationDetails.ENTRY_SCHEDULED,
                created_by=request.session.get('loginid')
            )

        messages.success(request, "Roaster updated successfully!")
        return redirect(f"{reverse('roaster_list')}?page={current_page}")
    
    
class StartTransportView(View):
    def post(self, request, roaster_id):
        try:
            roaster = get_object_or_404(Roaster, id=roaster_id)
            user_id = request.session.get('loginid')
            
            current_transports = PlayerTransportationDetails.objects.filter(
                roasterId=roaster,
                status_flag=1
            )
            
            for transport in current_transports:
                PlayerTransportationDetails.objects.create(
                    playerId=transport.playerId,
                    roasterId=roaster,
                    entry_status=PlayerTransportationDetails.ENTRY_STARTED,
                    created_by=user_id
                )
            
            return JsonResponse({
                'success': True,
                'new_status': 'STARTED'
            })
            
        except Exception as e:
            print("Error starting transport:", str(e))
            return JsonResponse({
                'success': False,
                'message': f'Error starting transport: {str(e)}'
            }, status=400)

class EndTransportView(View):
    def post(self, request, roaster_id):
        try:
            roaster = get_object_or_404(Roaster, id=roaster_id)
            user_id = request.session.get('loginid')
            
            current_transports = PlayerTransportationDetails.objects.filter(
                roasterId=roaster,
                status_flag=1,
                entry_status=PlayerTransportationDetails.ENTRY_STARTED
            )
            
            for transport in current_transports:
                PlayerTransportationDetails.objects.create(
                    playerId=transport.playerId,
                    roasterId=roaster,
                    details=transport.details,
                    entry_status=PlayerTransportationDetails.ENTRY_ENDED,
                    created_by=user_id
                )
            
            return JsonResponse({
                'success': True,
                'message': f'New timeline entries created.',
                'new_status': 'ENDED'
            })
            
        except Exception as e:
            print("Error ending transport:", str(e))
            return JsonResponse({
                'success': False,
                'message': f'Error ending transport: {str(e)}'
            }, status=400)
    
   
class EnquiryListView(View):
    template_name = "enquiry.html"

    def get(self, request):
        search_query = request.GET.get('search', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        status_filter = request.GET.get('status', '')
        page_number = request.GET.get('page', 1)

        enquiries = EnquiryDetails.objects.select_related('player')\
                                         .prefetch_related('playerenquiryresponses_set__user')\
                                         .order_by('-created_on')

        # Apply search filter
        if search_query:
            enquiries = enquiries.filter(
                Q(player__name__icontains=search_query) |
                Q(message__icontains=search_query) |
                Q(playerenquiryresponses__rnquiry_response__icontains=search_query)
            ).distinct()

        # Apply status filter
        if status_filter:
            if status_filter == 'pending':
                enquiries = enquiries.filter(is_replied=False)
            elif status_filter == 'replied':
                enquiries = enquiries.filter(is_replied=True)

        # Apply date range filter
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                enquiries = enquiries.filter(created_on__date__gte=start_date_obj)
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                enquiries = enquiries.filter(created_on__date__lte=end_date_obj)
            except ValueError:
                pass

        paginator = Paginator(enquiries, per_page)
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'enquiries': page_obj.object_list,
            'search_query': search_query,
            'start_date': start_date,
            'end_date': end_date,
            'status_choices': [
                ('', 'All'),
                ('pending', 'Pending'),
                ('replied', 'Replied')
            ]
        }
        return render(request, self.template_name, context)

    def post(self, request):
        enquiry_id = request.POST.get('enquiry_id')
        response_text = request.POST.get('response')
        user_id = request.session.get('loginid')

        
        try:
            enquiry = EnquiryDetails.objects.get(id=enquiry_id)
            user = MstUserLogins.objects.get(id=user_id)
            
            # Create the response
            enquiry_response = PlayerEnquiryResponses.objects.create(
                enquiry=enquiry,
                user=user,
                rnquiry_response=response_text
            )
            enquiry.is_replied = True
            enquiry.save()
            
            # Send email notification to player
            self._send_enquiry_reply_email(enquiry, response_text, user)
            
            try:
                device_tokens = UserDeviceToken.objects.filter(
                    user_email=enquiry.player.email,
                    status_flag=1
                ).values_list('device_token', flat=True)

                title = f"Enquiry #{enquiry.id} Replied"
                body = response_text[:100] + "..." if len(response_text) > 100 else response_text
                print("sending notification for enquiry", enquiry.id)

                for token in device_tokens:
                    if token:
                        try:
                            send_push_notification(request, token, title, body)
                            print(f"Push sent to token: {token}")
                        except Exception as e:
                            print(f"Failed to send push to token {token}: {str(e)}")

            except Exception as e:
                print(f"Error sending push notifications: {str(e)}")
            
            # Log user activity
            log_user_activity(request, "Enquiry Response", f"Replied to enquiry ID #{enquiry_id}")
            
            return JsonResponse({
                'success': True,
                'message': 'Response sent successfully!'
            })
            
        except EnquiryDetails.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Enquiry not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _send_enquiry_reply_email(self, enquiry, response_text, admin_user):
        """Send email notification to player about enquiry reply"""
        try:
            player = enquiry.player
            context = {
                'player_name': player.name,
                'enquiry_id': enquiry.id,
                'admin_message': response_text,
                'admin_name': admin_user.name if hasattr(admin_user, 'name') else "Admin Team",
                'reply_date': timezone.now().strftime("%B %d, %Y at %I:%M %p"),
                'original_enquiry': enquiry.message[:100] + "..." if len(enquiry.message) > 100 else enquiry.message
            }
            
            html_message = render_to_string('enquiry_reply_to_player.html', context)
            
            subject = f"Reply to Your Enquiry #E{enquiry.id} - FWC 2025"
            
            email_log = EmailLog.objects.create(
                email_type='ENQ_REPLY_TO_PLAYER',
                subject=subject,
                recipient_email=player.email,
                status='PENDING',
                html_content=html_message,
                text_content=f"Reply to your enquiry #{enquiry.id}. Message: {response_text[:100]}...",
            )

            send_mail(
                subject=subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[player.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Update email log with success
            email_log.status = 'SENT'
            email_log.save()
            
            print(f"Enquiry reply email sent successfully to {player.email}")
            
        except Exception as e:
            # Log the error but don't break the main functionality
            print(f"Failed to send enquiry reply email: {str(e)}")
            # If email log was created, update its status to failed
            if 'email_log' in locals():
                email_log.status = 'FAILED'
                email_log.save()


class DeptPlayerView(View):
    template_name = "dept_player.html"

    def get(self, request):
        """
        Render player management page with players data and search functionality.
        """
        # Get search query
        search_query = request.GET.get('q', '')
        
        # Filter players
        players = Players.objects.filter(status_flag=1).order_by("-id")
        
        # Apply search filter
        if search_query:
            players = players.filter(
                models.Q(name__icontains=search_query) |
                models.Q(email__icontains=search_query) |
                models.Q(fide_id__icontains=search_query) |
                models.Q(countryid__country_name__icontains=search_query)
            )
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(players, per_page)
        current_page = paginator.page(page)

        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        
        # Hotel choices
        HOTEL_CHOICES = [
            ('Rio Resort', 'Rio Resort'),
            ('Rio Boutique', 'Rio Boutique'),
        ]
        
        player_ids = [player.id for player in current_page]
        player_documents = PlayerDocument.objects.filter(
            player_id__in=player_ids,
            status_flag=1
        )
        
        documents_dict = {}
        for doc in player_documents:
            if doc.player_id not in documents_dict:
                documents_dict[doc.player_id] = []
            documents_dict[doc.player_id].append(doc)
        
        context = {
            "players": current_page,
            "countries": countries,
            "MstUserLogins": MstUserLogins,
            "search_query": search_query,
            "paginator": paginator,
            "page_obj": current_page,
            "hotel_choices": HOTEL_CHOICES,
            "documents_dict": documents_dict,
        }
        
        return render(request, self.template_name, context)

    def post(self, request):
        """
        Handle hotel and room assignment
        """
        try:
            player_id = request.POST.get('player_id')
            hotel = request.POST.get('hotel')
            room_no = request.POST.get('room_no')
            
            player = Players.objects.get(id=player_id, status_flag=1)
            player.hotel = hotel
            player.room_no = room_no
            player.save()
            
            messages.success(request, f'Successfully assigned {hotel} - Room {room_no} to {player.name}')
            
        except Players.DoesNotExist:
            messages.error(request, 'Player not found')
        except Exception as e:
            messages.error(request, f'Error assigning room: {str(e)}')
        
        return redirect('DeptAccFBPlayers')
        
        
class DeptPlayerProfile(View):
    template_name = "dept_player_profile.html"

    def get(self, request, player_id):
        player = get_object_or_404(Players, id=player_id, status_flag=1)
        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        TransportationTypes = TransportationType.objects.filter(status_flag=1).order_by("Name")
        player_documents = PlayerDocument.objects.filter(player=player, status_flag=1)
        
        transportation_details = PlayerTransportationDetails.objects.filter(
            playerId=player, 
        ).select_related('roasterId').order_by('-travel_date', '-created_on')
        
        return render(request, self.template_name, {
            "player": player, 
            "countries": countries, 
            "TransportationTypes": TransportationTypes,
            "player_documents": player_documents,
            "transportation_details": transportation_details
        })
        

class PlayerLogisticsView(ListView):
    model = Players
    template_name = 'player_logistic.html'
    context_object_name = 'players'
    paginate_by = per_page
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(status_flag=1).order_by('-created_on')
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_date = timezone.now().date()
        cutoff_date = timezone.datetime(2025, 11, 3).date()
        show_arrival = current_date <= cutoff_date

        for player in context['players']:
            transport_records = PlayerTransportationDetails.objects.filter(
                playerId=player,
                status_flag=1
            ).exclude(entry_status=PlayerTransportationDetails.ENTRY_SCHEDULED).order_by('-created_on')
            
            has_arrived = transport_records.filter(
                entry_status=PlayerTransportationDetails.ENTRY_ARRIVED_AIRPORT
            ).exists()
            
            has_departed = transport_records.filter(
                entry_status=PlayerTransportationDetails.ENTRY_REACHED_AIRPORT_DEPARTURE
            ).exists()
            
            latest_transport = transport_records.first()
            if latest_transport:
                player.current_transport_status = latest_transport.player_status_display
            else:
                player.current_transport_status = ""
            
            player.has_arrived_status = has_arrived
            player.has_departure_status = has_departed
            
            if show_arrival:
                player.show_arrival_button = not has_arrived
                player.show_departure_button = False
            else:
                player.show_departure_button = not has_departed
                player.show_arrival_button = False

        context.update({
            'search_query': self.request.GET.get('search', ''),
            'show_arrival': show_arrival,
            'current_date': current_date,
            'cutoff_date': cutoff_date,
        })
        log_user_activity(self.request, "View Player Logistic", "Viewed player logistic page")

        return context
        

class MarkPlayerStatusView(View):
    def post(self, request, player_id):
        try:
            data = json.loads(request.body)
            player = get_object_or_404(Players, id=player_id)
            user_id = request.session.get('loginid')
            
            is_departure = data.get('is_departure', False)
            
            if is_departure:
                entry_status = PlayerTransportationDetails.ENTRY_REACHED_AIRPORT_DEPARTURE
                status_display = "Reached Airport for Departure"
                details = "Player marked as reached airport for departure"
            else:
                entry_status = PlayerTransportationDetails.ENTRY_ARRIVED_AIRPORT
                status_display = "Arrived Airport"
                details = "Player marked as arrived at airport"
            
            # Check if status already exists to prevent duplicates
            existing_status = PlayerTransportationDetails.objects.filter(
                playerId=player,
                entry_status=entry_status
            ).first()
            
            if existing_status:
                return JsonResponse({
                    'success': False,
                    'message': f'{player.name} is already marked as {status_display}.'
                }, status=400)
            
            # Create new transport entry
            PlayerTransportationDetails.objects.create(
                playerId=player,
                entry_status=entry_status,
                details=details,
                remarks=f"Status changed to {status_display} by user {user_id}",
                created_by=user_id
            )
            
            log_user_activity(
                request, 
                "Mark Player Status", 
                f"Player ID({player_id}) - {player.name} marked as {status_display}"
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{player.name} marked as {status_display} successfully.',
                'new_status': status_display
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            print("Error updating status:", e)
            return JsonResponse({
                'success': False,
                'message': f'Error updating status: {str(e)}'
            }, status=400)
            
            
            
class PlayersExportView(View):
    
    def get(self, request):
        """Export players to Excel with formatted output matching HTML display"""
        try:
            # Get all players data
            players = Players.objects.filter(status_flag=1).prefetch_related(
                Prefetch(
                    'playertransportationdetails_set',
                    queryset=PlayerTransportationDetails.objects.filter(status_flag=1).order_by('-created_on'),
                    to_attr='latest_transports'
                )
            ).order_by("-id")

            # Prepare data for export
            export_data = []
            for player in players:
                latest_transport = player.latest_transports[0] if player.latest_transports else None
                transportation_status = latest_transport.player_status_display if latest_transport else "Not Set"

                export_data.append({
                    'player_id': f"P{player.id}",
                    'player_name': player.name,
                    'fide_id': getattr(player, 'fide_id', ''),
                    'age': getattr(player, 'age', ''),
                    'gender': getattr(player, 'gender', ''),
                    'country': player.countryid.country_name if player.countryid else '',
                    'email': player.email,
                    'status': player.get_status_display() if player.status else '',
                    'transportation_status': transportation_status,
                    'created_date': player.created_on.strftime("%d %b %Y") if player.created_on else '',
                })

            # Convert to DataFrame
            df = pd.DataFrame(export_data)

            # Rename columns for Excel display to match HTML
            if not df.empty:
                df.rename(
                    columns={
                        'player_id': 'Player ID',
                        'player_name': 'Player Name',
                        'fide_id': 'FIDE ID',
                        'age': 'Age',
                        'gender': 'Gender',
                        'country': 'Country',
                        'email': 'Email',
                        'status': 'Status',
                        'transportation_status': 'Transportation Status',
                        'created_date': 'Registration Date',
                    },
                    inplace=True
                )
                
            df = df.replace([float('inf'), float('-inf')], None)
            df = df.fillna("")  # or .fillna("N/A") if you want


            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Write data starting from row 2 to leave space for title
                df.to_excel(writer, sheet_name="Players Report", startrow=2, index=False)

                workbook = writer.book
                worksheet = writer.sheets["Players Report"]

                # Add title
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 16,
                    'align': 'center',
                })

                date_format = workbook.add_format({
                    'bold': False,
                    'font_size': 12,
                    'align': 'center',
                })

                # Write title
                worksheet.merge_range('A1:J1', 'PLAYERS REPORT', title_format)
                worksheet.merge_range('A2:J2', f'Generated on: {datetime.now().strftime("%d %b %Y at %I:%M %p")}', date_format)

                # Add header formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#271f64',
                    'font_color': 'white',
                    'border': 1,
                    'align': 'center',
                })

                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(2, col_num, value, header_format)

                # Add data formatting
                data_format = workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                })

                # Apply data format to all data cells
                for row_num in range(3, len(df) + 3):
                    for col_num in range(len(df.columns)):
                        worksheet.write(row_num, col_num, df.iat[row_num-3, col_num], data_format)

                # Set column widths
                column_widths = {
                    'Player ID': 12,
                    'Player Name': 25,
                    'FIDE ID': 15,
                    'Age': 8,
                    'Gender': 10,
                    'Country': 15,
                    'Email': 25,
                    'Status': 15,
                    'Transportation Status': 20,
                    'Registration Date': 15,
                }

                # Apply column widths
                for col_num, column_name in enumerate(df.columns):
                    width = column_widths.get(column_name, 15)
                    worksheet.set_column(col_num, col_num, width)

                # Add autofilter
                worksheet.autofilter(2, 0, len(df) + 2, len(df.columns) - 1)

                # Freeze header row and title
                worksheet.freeze_panes(3, 0)

            # Prepare response
            output.seek(0)
            filename = f"Players_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            response = HttpResponse(
                output,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            log_user_activity(request, "Export Players", "Players data exported to Excel")
            return response

        except Exception as e:
            return HttpResponse(f"Error exporting data: {str(e)}", status=500)
        
        
class DisableRoasterView(View):
    def post(self, request, roaster_id):
        try:
            print("roaster_id", roaster_id)
            log_user_activity(request, "Disable Roaster", f"Roaster ID({roaster_id}) has been disabled")
            roaster = Roaster.objects.get(id=roaster_id)
            roaster.status_flag = 0
            roaster.save()
            return JsonResponse({"success": True, "message": "Roaster has been disabled successfully."})
        except Roaster.DoesNotExist:
            return JsonResponse({"success": False, "message": "Roaster not found."}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)