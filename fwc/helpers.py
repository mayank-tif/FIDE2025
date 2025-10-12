import hashlib
import re
from .models import *
import random
import pandas as pd
   

# =================Convert password into encryption=============
def str_encrypt(password):
    sha256 = hashlib.sha256(password.encode())
    pass_enc = sha256.hexdigest()
    return pass_enc
# =============================END==============================


# ==========Validate Mobile number function===============
def mobile_number_validation(mobileno):

    mobile_startwith = '6,7,8,9'
    mobile_length = 10

    regex = re.compile('[@_!#$%^&*()<>?/}{~:.+=`?,;"| ]')
    if pd.isnull(mobileno) or mobileno == '':
        return 'mobile number should not be empty..!'
    elif not mobileno.isdigit():
        return 'Please give only numbers.'
    elif not mobileno.startswith(tuple(mobile_startwith)):
        return 'mobile number should start with {}..!'.format(mobile_startwith)
    elif regex.search(mobileno) is not None:
        return 'mobile number should not contain any special character (@_!#$%^&*()<>?/}{~:.+=`?,;"| )'
    elif len(mobileno) < mobile_length:
        return 'mobile number length not less than {}..!'.format(mobile_length)
    elif len(mobileno) > mobile_length:
        return 'mobile number length not greater than {}..!'.format(mobile_length)


# =======================--END--=============================================


def log_user_activity(request, action, description=None):
    try:
        user_id = request.session.get("loginid")
        if not user_id:
            return
        
        UserActivityLog.objects.create(
            user_id=user_id,
            action=action,
            description=description,
            created_on=timezone.now()
        )
    except Exception as e:
        print("Error logging activity:", e)