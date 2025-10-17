from rest_framework import serializers
from fwc.models import *
from datetime import datetime
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from FWC2025.env_details import *
from fwc.helpers import *
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class GenerateAppTokenSerializer(serializers.Serializer):
    deviceid = serializers.CharField(max_length=250, required=True, allow_blank=False)
    

class FideIDCheckSerializer(serializers.Serializer):
    fide_id = serializers.CharField(max_length=100, required=True)
    
    
class PlayerOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    fide_id = serializers.CharField(max_length=250, required=True, allow_blank=False)

    def validate(self, attrs):
        fide_id = attrs.get("fide_id")
        fide = FideIDMst.objects.filter(fide_id=fide_id).first()
        if not fide: 
            raise serializers.ValidationError({"error": {"message": "The provided FIDE ID is not registered. Please check your FIDE ID or contact administrators.."}})
        return attrs

class PlayerRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=500, required=True)
    password = serializers.CharField(max_length=200, required=True, write_only=True)
    fide_id = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=True, write_only=True)

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long.")
        return value
    

class PlayerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    deviceid = serializers.CharField(max_length=250, required=True, allow_blank=False)
    device_token = serializers.CharField(max_length=250, required=False, allow_blank=False)

    def validate(self, attrs):
        email = attrs.get('email')
        raw_password = attrs.get('password')
        deviceid = attrs.get('deviceid')
        encrypted_password = str_encrypt(str(raw_password))
        customers_qs = Players.objects.filter(email=email)
        if not customers_qs.exists():
            raise serializers.ValidationError({"error": {"message": "Customer does not exist"}})
        try:
            player = customers_qs.get(securepassword=encrypted_password, status_flag=1)
        except Players.DoesNotExist:
            raise serializers.ValidationError({"error": {"message": "Invalid email or password"}})

        attrs['player'] = player
        return attrs


class VerifyCustLoginOTPSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=250, required=True, allow_blank=False)
    otp = serializers.CharField(max_length=8, required=True, allow_blank=False)
    deviceid = serializers.CharField(max_length=250, required=True, allow_blank=False)
    device_token = serializers.CharField(max_length=250, required=False, allow_blank=False)
    
    def validate(self, validated_data):        
        if not Players.objects.filter(email=validated_data['email'], status_flag=1).exists():
            raise serializers.ValidationError({"error": {"message": "Email is not registered with us!!"}})
        if Players.objects.filter(email=validated_data['email'], status_flag=0).exists():
            raise serializers.ValidationError({"error": {"message": "Email is deactivated!!"}})
        return validated_data
    
    
class GetCustomerPtsSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=250, required=True, allow_blank=False)
    
    def validate(self, validated_data):        
        if not Players.objects.filter(email=validated_data['email'], status_flag=1).exists():
            raise serializers.ValidationError({"error": {"message": "Email is not registered with us!!"}})
        if Players.objects.filter(email=validated_data['email'], status_flag=0).exists():
            raise serializers.ValidationError({"error": {"message": "Email is deactivated!!"}})
        return validated_data
    

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']   
            

class TransportationDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    transportation_type_details = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayerTransportationDetails
        fields = [
            'id',
            'pickup_location',
            'drop_location',
            'details',
            'remarks',
            'status',
            'status_display',
            'travel_date',
            'created_on',
            'transportation_type_details'
        ]
    
    def get_transportation_type_details(self, obj):
        if obj.transportationTypeId:
            return {
                'id': obj.transportationTypeId.id,
                'name': obj.transportationTypeId.Name
            }
        return None

class RoasterTransportationSerializer(serializers.ModelSerializer):
    player_transportations = serializers.SerializerMethodField()
    
    class Meta:
        model = Roaster
        fields = [
            'id',
            'vechicle_type',
            'vechicle_no',
            'number_of_seats',
            'driver_name',
            'player_transportations',
            'created_on'
        ]
    
    def get_player_transportations(self, obj):
        # Get all transportation details for this specific roaster and player
        player_id = self.context.get('player_id')
        transports = PlayerTransportationDetails.objects.filter(
            roasterId=obj,
            playerId_id=player_id,
            status_flag=1
        ).select_related('transportationTypeId').order_by('-travel_date', '-created_on')
        
        return TransportationDetailSerializer(transports, many=True).data
    

class PlayerIDRequestSerializer(serializers.Serializer):
    player_id = serializers.IntegerField(required=True)
    
    def validate_player_id(self, value):
        try:
            player = Players.objects.get(id=value, status_flag=1)
            print("player 1234", value)
        except Players.DoesNotExist:
            raise serializers.ValidationError("Player not found or inactive")
        return player        
     
        
class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        # check password match
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"error": {"message": "New password and confirm password do not match."}}
            )

        email = data.get("email")
        user = Players.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError(
                {"error": {"message": "User with this email does not exist."}}
            )
        if user.status_flag==0:
            raise serializers.ValidationError(
                {"error": {"message": "User is deactivated. Please contact administrator."}}
            )

        data["user"] = user
        return data

    def save(self, **kwargs):
        user = self.validated_data["user"]
        new_password = self.validated_data["new_password"]
        user.securepassword = str_encrypt(str(new_password))
        user.save()
        return {"message": "Password updated successfully."}
     

class AnnouncementNotificationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcements
        fields = [
            'id',
            'title',
            'details',
            'created_by',
            'created_by_name',
            'created_on',
            'updated_on',
            'is_read'
        ]
    
    def get_is_read(self, obj):
        return False
    
    
class ContactFormSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=True)
    email = serializers.CharField(max_length=200, required=True)
    subject = serializers.CharField(max_length=500, required=True)
    message = serializers.CharField(required=True)
    
    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Please enter a valid email address.")
        return value
    
    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return value.strip()
    
    def validate_subject(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Subject must be at least 5 characters long.")
        return value.strip()
    
    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value.strip()
    

class EnquiryCreateSerializer(serializers.Serializer):
    player_id = serializers.IntegerField(required=True)
    message = serializers.CharField(required=True)
    
    def validate_player_id(self, value):
        try:
            player = Players.objects.get(id=value, status_flag=1)
        except Players.DoesNotExist:
            raise serializers.ValidationError("Player not found or inactive")
        return value
    
    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value.strip()

class EnquiryListSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.name', read_only=True)
    player_fide_id = serializers.CharField(source='player.fide_id', read_only=True)
    
    class Meta:
        model = EnquiryDetails
        fields = [
            'id',
            'player',
            'player_name',
            'player_fide_id',
            'message',
            'response',
            'created_on',
            'status_flag'
        ]


class RaiseComplaintSerializer(serializers.Serializer):
    description = serializers.CharField(required=True)
    department_id = serializers.IntegerField(required=True)
    
    def validate_department_id(self, value):
        try:
            department = Department.objects.get(id=value, status_flag=1)
        except Department.DoesNotExist:
            raise serializers.ValidationError("Department not found or inactive")
        return value
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return value.strip()

class ReplyToComplaintSerializer(serializers.Serializer):
    complaint_id = serializers.IntegerField(required=True)
    message = serializers.CharField(required=True)
    
    def validate_complaint_id(self, value):
        try:
            complaint = PlayerComplaint.objects.get(id=value, status_flag=1)
        except PlayerComplaint.DoesNotExist:
            raise serializers.ValidationError("Complaint not found or inactive")
        return value
    
    def validate_message(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Message must be at least 5 characters long.")
        return value.strip()

class ComplaintConversationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_type = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayerComplaintConversation
        fields = [
            'id',
            'message',
            'sender_name',
            'sender_type',
            'created_on'
        ]
    
    def get_sender_name(self, obj):
        if obj.sender_player:
            return obj.sender_player.name
        elif obj.sender_user:
            return obj.sender_user.name
        return "Unknown"
    
    def get_sender_type(self, obj):
        if obj.sender_player:
            return "player"
        elif obj.sender_user:
            return "admin"
        return "unknown"

class ComplaintListSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    conversations = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayerComplaint
        fields = [
            'id',
            'player_name',
            'description',
            'status',
            'department_name',
            'created_on',
            'updated_on',
            'conversations'
        ]
    
    def get_conversations(self, obj):
        conversations = obj.conversations.filter(status_flag=1).order_by('created_on')
        return ComplaintConversationSerializer(conversations, many=True).data