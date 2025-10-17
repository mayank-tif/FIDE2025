# from django.conf import settings
# import firebase_admin
# from firebase_admin import credentials, messaging

# firebase_creds = {
#     "type": settings.TYPE,
#     "project_id": settings.PROJECT_ID,
#     "private_key_id": settings.PRIVATE_KEY_ID,
#     "private_key": settings.PRIVATE_KEY.replace("\\n", "\n"),
#     "client_email": settings.CLIENT_EMAIL,
#     "client_id": settings.CLIENT_ID,
#     "auth_uri": settings.AUTH_URL,
#     "token_uri": settings.TOKEN_URL,
#     "auth_provider_x509_cert_url": settings.AUTH_PROVIDER_X509_CERT_URL,
#     "client_x509_cert_url": settings.CLIENT_X509_CERT_URL,
#     "universe_domain": settings.UNIVERSE_DOMAIN,
# }

# # Initialize Firebase app only once
# if not firebase_admin._apps:
#     cred = credentials.Certificate(firebase_creds)
#     firebase_admin.initialize_app(cred)


# def send_push_notification(token, title, body):
#     message = messaging.Message(
#         notification=messaging.Notification(
#             title=title,
#             body=body
#         ),
#         token=token
#     )
#     response = messaging.send(message)
#     return response
