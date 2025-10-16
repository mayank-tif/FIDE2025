from django.db import models
from django.utils import timezone
from django.db.models import Max
import string
import secrets
import math
import datetime
import logging
logger = logging.getLogger(__name__)


class MstRole(models.Model):
    id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=20)
    role_code = models.CharField(max_length=20, unique=True)
    status_flag = models.IntegerField(default=1)

    def __str__(self):
        return self.role_name
    
    class Meta:
        db_table = 'Role'
        
        
class Department(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, null=True)
    status_flag = models.IntegerField(default=1)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)

    def __int__(self):
        return self.department_id
    
    class Meta:
        db_table = 'Department'
        
        
        
class CountryMst(models.Model):
    country_id = models.AutoField(primary_key=True)
    country_name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=50, null=True)
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    def __str__(self):
        return self.states_name
    
    class Meta:
        db_table = 'CountryMst'

        
class StateMst(models.Model):
    states_id = models.AutoField(primary_key=True)
    states_name = models.CharField(max_length=50)
    states_code = models.CharField(max_length=50, null=True)
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    def __str__(self):
        return self.states_name
    
    class Meta:
        db_table = 'StateMst'
        


class CityMst(models.Model):
    city_id = models.AutoField(primary_key=True)
    city_name = models.CharField(max_length=50)
    city_code = models.CharField(max_length=50, null=True)
    state_id = models.ForeignKey(StateMst, on_delete=models.DO_NOTHING, null=True)
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    def __str__(self):
        return self.city_name
    
    class Meta:
        db_table = 'CityMst'
    

class MstUserLogins(models.Model):    
    GENDER_MALE = "MALE"
    GENDER_FEMALE = "FEMALE"
    GENDER_OTHER = "OTHER"

    GENDER_CHOICES = [
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500, null=True)
    email = models.CharField(max_length=50, null=True)
    loginname = models.CharField(max_length=20)
    securepassword = models.CharField(max_length=200, null=True)
    roleid = models.ForeignKey(MstRole, on_delete=models.DO_NOTHING, null=True, db_column='roleId')
    countryid = models.ForeignKey(CountryMst, on_delete=models.DO_NOTHING, null=True, db_column='countryId')
    mobilenumber = models.CharField(max_length=15, null=True)
    deactivated_by = models.IntegerField(null=True)
    status_flag = models.IntegerField(default=1)
    gender = models.CharField(max_length=10,choices=GENDER_CHOICES,null=True,blank=True)
    deactivated_on = models.DateTimeField(null=True)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, null=True, db_column='departmentId')

    def __str__(self):
        return self.loginname
    
    class Meta:
        unique_together = (('loginname',),)
        db_table = 'UserLogins'
        
        
        
        
class Players(models.Model):
    STATUS_ACTIVE = "ACTIVE"
    STATUS_DEPARTED = "DEPARTED"
    STATUS_KNOCKED_OUT = "KNOCKED_OUT"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_DEPARTED, "Departed"),
        (STATUS_KNOCKED_OUT, "Knocked Out"),
    ]
    
    GENDER_MALE = "MALE"
    GENDER_FEMALE = "FEMALE"
    GENDER_OTHER = "OTHER"

    GENDER_CHOICES = [
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
    ]
    
    ROOM_CLEANING_MORNING = "MORNING"
    ROOM_CLEANING_AFTERNOON = "AFTERNOON"
    ROOM_CLEANING_EVENING = "EVENING"
    ROOM_CLEANING_AT_HOTEL = "AT_HOTEL"

    ROOM_CLEANING_CHOICES = [
        (ROOM_CLEANING_MORNING, "Morning"),
        (ROOM_CLEANING_AFTERNOON, "Afternoon"),
        (ROOM_CLEANING_EVENING, "Evening"),
        (ROOM_CLEANING_AT_HOTEL, "At Hotel"),
    ]
    
    id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    documents = models.FileField(upload_to='player_documents/', null=True, blank=True)
    fide_id = models.CharField(max_length=100, null=True)
    age = models.IntegerField(null=True)
    name = models.CharField(max_length=500, null=True)
    address = models.CharField(max_length=250, null=True)
    email = models.CharField(max_length=50, null=True)
    loginname = models.CharField(max_length=20)
    securepassword = models.CharField(max_length=200, null=True)
    cityid = models.IntegerField(null=True)
    stateid = models.IntegerField(null=True)
    countryid = models.ForeignKey(CountryMst, on_delete=models.DO_NOTHING, null=True, blank=True, db_column='countryId')
    mobilenumber = models.CharField(max_length=15, null=True)
    deactivated_by = models.IntegerField(null=True)
    status_flag = models.IntegerField(default=1)
    status = models.CharField(max_length=50,choices=STATUS_CHOICES,default=STATUS_ACTIVE,null=True)
    gender = models.CharField(max_length=10,choices=GENDER_CHOICES,null=True,blank=True)
    deactivated_on = models.DateTimeField(null=True)
    last_log_id = models.IntegerField(null=True)
    profile_pic = models.CharField(max_length=100, null=True)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    details = models.TextField(null=True)
    room_cleaning_preference = models.CharField(max_length=15,choices=ROOM_CLEANING_CHOICES,null=True,blank=True)
    is_self_registered = models.BooleanField(default=True)
    accompanying_persons = models.TextField(null=True)

    def __str__(self):
        return self.loginname
    
    class Meta:
        db_table = 'Players'
        verbose_name = 'Player'
        verbose_name_plural = 'Players'
        unique_together = (('email',),)
        

class PlayerDocument(models.Model):
    id = models.AutoField(primary_key=True)
    player = models.ForeignKey(Players, on_delete=models.DO_NOTHING, related_name='player_documents')
    reg_document = models.FileField(upload_to='player_reg_documents/')
    document_type = models.CharField(max_length=100, default='IDENTIFICATION')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()  # in bytes
    uploaded_at = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'PlayerDocument'
        
        
class TransportationType(models.Model):
    id = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    status_flag = models.IntegerField(default=1)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)

    def __str__(self):
        return self.Name
    
    class Meta:
        db_table = 'TransportationType'
        
        
        
class Roaster(models.Model):
    id = models.AutoField(primary_key=True)
    vechicle_no = models.CharField(max_length=100, null=False)
    vechicle_type = models.TextField(null=False)
    number_of_seats = models.IntegerField(null=False)
    driver_name = models.CharField(max_length=100, null=False)
    transportationTypeId = models.ForeignKey(TransportationType, on_delete=models.DO_NOTHING, db_column='transportationTypeId')
    status_flag = models.IntegerField(default=1)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    

    def __str__(self):
        return self.id
    
    class Meta:
        db_table = 'Roaster'
        
        
class PlayerTransportationDetails(models.Model):
    STATUS_ARRIVED_AIRPORT = "ARRIVED_AIRPORT"
    STATUS_ENTROUTE_HOTEL = "ENTROUTE_HOTEL"
    STATUS_REACHED_HOTEL = "REACHED_HOTEL"
    STATUS_IN_TRANSIT = "IN_TRANSIT"
    STATUS_REACHED_DESTINATION = "REACHED_DESTINATION"
    STATUS_DEPARTED_AIRPORT = "DEPARTED_AIRPORT"
    STATUS_REACHED_AIRPORT_DEPARTURE = "REACHED_AIRPORT_DEPARTURE"

    STATUS_CHOICES = [
        (STATUS_ARRIVED_AIRPORT, "Arrived at Airport"),
        (STATUS_ENTROUTE_HOTEL, "Entroute to Hotel"),
        (STATUS_REACHED_HOTEL, "Reached Hotel"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_REACHED_DESTINATION, "Reached Destination"),
        (STATUS_DEPARTED_AIRPORT, "Departed for Airport"),
        (STATUS_REACHED_AIRPORT_DEPARTURE, "Reached Airport for Departure"),
    ]
    
    id = models.AutoField(primary_key=True)
    playerId = models.ForeignKey(Players, on_delete=models.DO_NOTHING, db_column='playerId')
    roasterId = models.ForeignKey(Roaster, on_delete=models.DO_NOTHING, db_column='roasterId', null=True, blank=True)
    transportationTypeId = models.ForeignKey(TransportationType, on_delete=models.DO_NOTHING, db_column='transportationTypeId', null=True)
    pickup_location = models.CharField(max_length=500, null=True)
    drop_location = models.CharField(max_length=500, null=True)
    details = models.CharField(max_length=500, null=True)
    remarks = models.CharField(max_length=500, null=True)
    status = models.CharField(max_length=200, choices=STATUS_CHOICES, default=STATUS_IN_TRANSIT, null=True, blank=True)
    travel_date = models.DateTimeField(null=True)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    status_flag = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.playerId.name} - {self.pickup_location} to {self.drop_location}"
    
    class Meta:
        db_table = 'PlayerTransportationDetails' 
        

class PlayerComplaint(models.Model):
    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]

    id = models.AutoField(primary_key=True)
    player = models.ForeignKey(Players, on_delete=models.DO_NOTHING, db_column='playerId')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, db_column='departmentId')
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    status_flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'PlayerComplaint'

    def __str__(self):
        return f"{self.player.name} - {self.subject} ({self.status})"


class PlayerComplaintConversation(models.Model):
    id = models.AutoField(primary_key=True)
    complaint = models.ForeignKey(PlayerComplaint, on_delete=models.DO_NOTHING,related_name='conversations', db_column='complaintId')
    sender_player = models.ForeignKey(Players, on_delete=models.DO_NOTHING,null=True, blank=True, db_column='senderPlayerId')
    sender_user = models.ForeignKey(MstUserLogins, on_delete=models.DO_NOTHING,null=True, blank=True, db_column='senderUserId')
    message = models.TextField()
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'PlayerComplaintConversation'

    def __str__(self):
        return f"{self.complaint.id}"
    
    

class Announcements(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    details = models.TextField()
    created_by = models.ForeignKey(MstUserLogins, on_delete=models.DO_NOTHING,null=True, blank=True, db_column='createdBy')
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    status_flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'Announcements'

    def __str__(self):
        return f"{self.title} ({self.status})"
    
    
    
class AnnouncementRecipients(models.Model):
    id = models.AutoField(primary_key=True)
    announcement = models.ForeignKey(Announcements, on_delete=models.DO_NOTHING,related_name='recipients', db_column='announcementId')
    player = models.ForeignKey(Players, on_delete=models.DO_NOTHING, db_column='playerId')
    sent_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'AnnouncementRecipients'
        unique_together = ('announcement', 'player')  # Avoid duplicates

    def __str__(self):
        return f"Announcement '{self.announcement.title}' sent to {self.player.name}"
    
    
class UserActivityLog(models.Model):
    user = models.ForeignKey("MstUserLogins", on_delete=models.DO_NOTHING, related_name="activity_logs", null=True, blank=True)
    player = models.ForeignKey("Players", on_delete=models.DO_NOTHING, related_name="activity_logs", null=True, blank=True)
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "user_activity_log"
        ordering = ["-created_on"]

    def __str__(self):
        return f"{self.user.loginname} - {self.action} at {self.created_on.strftime('%Y-%m-%d %H:%M:%S')}"
    
    
class FideIDMst(models.Model):
    id = models.AutoField(primary_key=True)
    fide_id = models.CharField(max_length=100, null=True)
    player_name = models.CharField(max_length=100, null=True)
    Full_country_name = models.CharField(max_length=100, null=True)
    Short_country_name = models.CharField(max_length=20, null=True)
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'FideIDMst'


class PlayerRegistrationAuditLog(models.Model):
    # Audit log ID
    id = models.AutoField(primary_key=True)
    
    # Player information (all fields from Players model)
    player_id = models.IntegerField(null=True, blank=True, help_text="ID of the player if registration was successful")
    image = models.CharField(max_length=500, null=True, blank=True, help_text="Image file path")
    documents = models.CharField(max_length=500, null=True, blank=True, help_text="Document file path")
    fide_id = models.CharField(max_length=100, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=500, null=True, blank=True)
    address = models.CharField(max_length=250, null=True, blank=True)
    email = models.CharField(max_length=50, null=True, blank=True)
    loginname = models.CharField(max_length=20, null=True, blank=True)
    securepassword = models.CharField(max_length=200, null=True, blank=True)
    cityid = models.IntegerField(null=True, blank=True)
    stateid = models.IntegerField(null=True, blank=True)
    countryid = models.IntegerField(null=True, blank=True, help_text="Country ID from CountryMst")
    mobilenumber = models.CharField(max_length=15, null=True, blank=True)
    deactivated_by = models.IntegerField(null=True, blank=True)
    status_flag = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Players.STATUS_CHOICES, default=Players.STATUS_ACTIVE, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Players.GENDER_CHOICES, null=True, blank=True)
    deactivated_on = models.DateTimeField(null=True, blank=True)
    last_log_id = models.IntegerField(null=True, blank=True)
    profile_pic = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True, blank=True)
    updated_by = models.IntegerField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    room_cleaning_preference = models.CharField(max_length=15, choices=Players.ROOM_CLEANING_CHOICES, null=True, blank=True)
    accompanying_persons = models.TextField(null=True)
    
    # Additional form fields that are not in Players model
    food_allergies = models.TextField(null=True, blank=True, help_text="Food allergies information from form")
    document_file_name = models.CharField(max_length=255, null=True, blank=True, help_text="Original name of uploaded document")
    document_file_size = models.BigIntegerField(null=True, blank=True, help_text="Size of uploaded document in bytes")
    
    # Audit log specific fields
    submission_data = models.JSONField(default=dict, help_text="Raw form submission data")
    user_agent = models.TextField(null=True, blank=True, help_text="User agent string")
    submission_status = models.CharField(
        max_length=20,
        choices=[
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
            ('VALIDATION_ERROR', 'Validation Error'),
            ('DUPLICATE', 'Duplicate'),
        ],
        default='SUCCESS'
    )
    error_message = models.TextField(null=True, blank=True, help_text="Error message if submission failed")
    validation_errors = models.JSONField(default=dict, help_text="Form validation errors if any")
    
    # Timestamps
    submitted_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Audit Log - {self.name} ({self.email}) - {self.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        db_table = 'PlayerRegistrationAuditLog'
        verbose_name = 'Player Registration Audit Log'
        verbose_name_plural = 'Player Registration Audit Logs'

    def save(self, *args, **kwargs):
        if not self.processed_at and self.submission_status in ['SUCCESS', 'FAILED']:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)



class EnquiryDetails(models.Model):
    id = models.AutoField(primary_key=True)
    player= models.ForeignKey(Players, on_delete=models.DO_NOTHING, db_column='playerId')
    message = models.TextField()
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'EnquiryDetails'


class EmailLog(models.Model):
    
    STATUS_CHOICES = [
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]
    
    # Basic email information
    email_type = models.CharField(max_length=20, default='WELCOME')
    subject = models.CharField(max_length=255)
    recipient_email = models.EmailField()
    
    # Status and tracking
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    sent_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Related objects
    player = models.ForeignKey('Players', on_delete=models.CASCADE, related_name='email_logs', blank=True, null=True)
    audit_log = models.ForeignKey('PlayerRegistrationAuditLog', on_delete=models.SET_NULL, blank=True, null=True)
    
    # Email content (for debugging)
    html_content = models.TextField(blank=True, null=True)
    text_content = models.TextField(blank=True, null=True)
    
    # Technical details
    message_id = models.CharField(max_length=255, blank=True, null=True)  # SMTP message ID
    retry_count = models.IntegerField(default=0)
    
    # Standard fields
    status_flag = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_log'
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
    
    def __str__(self):
        return f"{self.email_type} to {self.recipient_email} - {self.status}"
    
    
    
class CustomerLoginOtpVerification(models.Model):
    class Meta:
        unique_together = (('mobileno', 'source'))

    id = models.AutoField(primary_key=True)
    mobileno = models.BigIntegerField(null=True)
    email = models.CharField(max_length=200, null=True)
    secureotp = models.CharField(max_length=256)
    source = models.CharField(max_length=50, null=True)
    flag = models.CharField(max_length=100, null=True)
    device_id = models.TextField(max_length=500, null=True)
    device_type = models.CharField(max_length=250, null=True)
    user_id = models.IntegerField(null=True)
    user_type = models.CharField(max_length=50, null=True)
    otp_expired_on = models.DateTimeField(null=True)
    support_remarks = models.TextField(max_length=500, null=True)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)
    
    def __int__(self):
        return self.id
    
    class Meta:
        db_table = 'PlayerLoginOtpVerification'
    
    
class UserDeviceToken(models.Model):
    id = models.AutoField(primary_key=True)
    user_email = models.CharField(max_length=200, null=True)
    device_token = models.TextField(max_length=500, null=True)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    status_flag = models.IntegerField(default=1)
    
    def __int__(self):
        return self.id
    
    class Meta:
        db_table = 'UserDeviceToken'