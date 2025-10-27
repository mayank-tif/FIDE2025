from django.conf import settings
import uuid
import firebase_admin
from firebase_admin import credentials, messaging
from FWC2025 import env_details as env


firebase_creds = {
    "type": settings.TYPE,
    "project_id": settings.PROJECT_ID,
    "private_key_id": settings.PRIVATE_KEY_ID,
    "private_key": settings.PRIVATE_KEY.replace("\\n", "\n"),
    "client_email": settings.CLIENT_EMAIL,
    "client_id": settings.CLIENT_ID,
    "auth_uri": settings.AUTH_URL,
    "token_uri": settings.TOKEN_URL,
    "auth_provider_x509_cert_url": settings.AUTH_PROVIDER_X509_CERT_URL,
    "client_x509_cert_url": settings.CLIENT_X509_CERT_URL,
    "universe_domain": settings.UNIVERSE_DOMAIN,
}

# Initialize Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)


def send_push_notification(request, token, title, body, device_type):
    if settings.NOTIFICATION_STATUS:
        print("sent notification", token)
        # message = messaging.Message(
        #     notification=messaging.Notification(
        #         title=title,
        #         body=body
        #     ),
        #     token=token
        # )
        base_url = f"{request.scheme}://{request.get_host()}"
        icon_url = "https://staging.fwc2025.in/static/assets/images/notification-icon-bg.png"
        notification_id = str(uuid.uuid4())
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
                image=icon_url,
            ),
            data={
                "click_action": env.NOTIFICATION_ON_CLICK,
                "notification_id": notification_id,
                "title": title,
                "body": body

            },
            token=token
        )

        response = messaging.send(message)
        return response
