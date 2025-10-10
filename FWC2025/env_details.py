import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

RFAPI_USERNAME = os.getenv('API_USERNAME')
RFAPI_PASSWORD = os.getenv('API_PASSWORD')
KX_SMS_API_KEY = os.getenv('KX_SMS_API_SECRET_KEY')
config_Registration_SMS_text = os.getenv('config_Reg_wecome_SMS_text')
config_Transaction_Pts_SMS_text = os.getenv('config_Trans_pts_SMS_text')
config_Pts_redemption_SMS_text = os.getenv('config_Pts_redemption_SMS_text')
CP67_APP_API_USERNAME = os.getenv('CP67APP_API_USERNAME')
CP67_APP_API_PASSWORD = os.getenv('CP67APP_API_PASSWORD')
CRM_APP_API_RF_USERNAME = os.getenv('CRM_APP_API_RF_USERNAME')
CRM_APP_API_RF_PASSWORD = os.getenv('CRM_APP_API_RF_PASSWORD')
config_login_otp_SMS_text = os.getenv('config_login_otp_SMS_text')
SCHEDULE_LOGGER_NAME = os.getenv('SCHEDULE_LOGGER_NAME')
SCHEDULE_LOG_FILE_NAME = os.getenv('SCHEDULE_LOG_FILE_NAME')
SCHEDULE_LOG_FILE_FORMAT =os.getenv('SCHEDULE_LOG_FILE_FORMAT')
SCHEDULE_LOGGING_LEVEL = os.getenv('SCHEDULE_LOGGING_LEVEL')
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

TYPE = os.getenv('TYPE')
PROJECT_ID=os.getenv('PROJECT_ID')
PRIVATE_KEY_ID=os.getenv('PRIVATE_KEY_ID')
PRIVATE_KEY=os.getenv('PRIVATE_KEY')
CLIENT_EMAIL=os.getenv('CLIENT_EMAIL')
CLIENT_ID=os.getenv('CLIENT_ID')
AUTH_URL=os.getenv('AUTH_URL')
TOKEN_URL=os.getenv('TOKEN_URL')
AUTH_PROVIDER_X509_CERT_URL=os.getenv('AUTH_PROVIDER_X509_CERT_URL')
CLIENT_X509_CERT_URL=os.getenv('CLIENT_X509_CERT_URL')
UNIVERSE_DOMAIN=os.getenv('UNIVERSE_DOMAIN')


