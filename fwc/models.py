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
    state_id = models.ForeignKey(StateMst, on_delete=models.CASCADE, null=True)
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
    age = models.IntegerField(null=True)
    name = models.CharField(max_length=500, null=True)
    address = models.CharField(max_length=250, null=True)
    email = models.CharField(max_length=50, null=True)
    loginname = models.CharField(max_length=20)
    securepassword = models.CharField(max_length=200, null=True)
    roleid = models.ForeignKey(MstRole, on_delete=models.CASCADE, null=True, db_column='roleId')
    cityid = models.IntegerField(null=True)
    stateid = models.IntegerField(null=True)
    countryid = models.ForeignKey(CountryMst, on_delete=models.DO_NOTHING, null=False, db_column='countryId')
    mobilenumber = models.CharField(max_length=15, null=True)
    deactivated_by = models.IntegerField(null=True)
    status_flag = models.IntegerField(default=1)
    gender = models.CharField(max_length=10,choices=GENDER_CHOICES,null=True,blank=True)
    deactivated_on = models.DateTimeField(null=True)
    last_log_id = models.IntegerField(null=True)
    profile_pic = models.CharField(max_length=100, null=True)
    created_by = models.IntegerField(null=True)
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True)
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, null=True, db_column='departmentId')

    def __str__(self):
        return self.loginname
    
    class Meta:
        # unique_together = (('loginname',),)
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
    
    id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    fide_id = models.IntegerField(null=True, unique=True)
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

    def __str__(self):
        return self.loginname
    
    class Meta:
        unique_together = (('email',),)
        db_table = 'Players'