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

    ROOM_CLEANING_CHOICES = [
        (ROOM_CLEANING_MORNING, "Morning"),
        (ROOM_CLEANING_AFTERNOON, "Afternoon"),
        (ROOM_CLEANING_EVENING, "Evening"),
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
    countryid = models.ForeignKey(CountryMst, on_delete=models.DO_NOTHING, null=False, db_column='countryId')
    mobilenumber = models.CharField(max_length=15, null=True)
    deactivated_by = models.IntegerField(null=True)
    status_flag = models.IntegerField(default=1)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_ACTIVE,null=True)
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

    def __str__(self):
        return self.loginname
    
    class Meta:
        db_table = 'Players'
        verbose_name = 'Player'
        verbose_name_plural = 'Players'
        unique_together = (('email',),)
        
        
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
        
        
class PlayerTransportationDetails(models.Model):
    STATUS_IN_TRANSIT = "IN_TRANSIT"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_PENDING = "PENDING"

    STATUS_CHOICES = [
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_PENDING, "Pending"),
    ]
    
    id = models.AutoField(primary_key=True)
    playerId = models.ForeignKey(Players, on_delete=models.DO_NOTHING, db_column='playerId')
    transportationTypeId = models.ForeignKey(TransportationType, on_delete=models.DO_NOTHING, db_column='transportationTypeId')
    pickup_location = models.CharField(max_length=500)
    drop_location = models.CharField(max_length=500)
    details = models.CharField(max_length=500)
    remarks = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_TRANSIT)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)

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



