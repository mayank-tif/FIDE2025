# from apns2.client import APNsClient
# from apns2.payload import Payload
# import json
# import os
# from django.conf import settings

# class APNSService:
#     def __init__(self):
#         # Configure these in your settings.py
#         self.auth_key_path = getattr(settings, 'APNS_AUTH_KEY_PATH', None)
#         self.key_id = getattr(settings, 'APNS_KEY_ID', None)
#         self.team_id = getattr(settings, 'APNS_TEAM_ID', None)
#         self.topic = getattr(settings, 'APNS_TOPIC', None)  # Your app bundle ID
#         self.use_sandbox = getattr(settings, 'APNS_USE_SANDBOX', True)
#         self.client = None
        
#     def get_client(self):
#         if not self.client and self.auth_key_path:
#             try:
#                 self.client = APNsClient(
#                     credentials=self.auth_key_path,
#                     use_sandbox=self.use_sandbox,
#                     use_alternative_port=False
#                 )
#             except Exception as e:
#                 print(f"APNS Client initialization error: {str(e)}")
#         return self.client
    
#     def send_notification(self, device_token, title, body, badge_count=1, custom_data=None):
#         """
#         Send push notification to iOS device via APNS
#         """
#         try:
#             client = self.get_client()
#             if not client:
#                 print("APNS client not initialized. Check your APNS configuration.")
#                 return None
            
#             # Create payload
#             payload = Payload(
#                 alert={
#                     "title": title,
#                     "body": body
#                 },
#                 badge=badge_count,
#                 sound="default",
#                 custom=custom_data or {}
#             )
            
#             # Send notification
#             response = client.send_notification(
#                 device_token,
#                 payload,
#                 topic=self.topic
#             )
            
#             print(f"APNS response: {response}")
#             return response
            
#         except Exception as e:
#             print(f"APNS Error: {str(e)}")
#             return None

# # Singleton instance
# apns_service = APNSService()