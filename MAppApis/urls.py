from django.urls import path
from .views import *

app_name = 'MAppApis'  # Define app_name here for namespacing

urlpatterns = [
    path('generate-app-token/', GenerateAppTokenView.as_view(), name='generate-app-token'),
    path('check-fide-id/', CheckFideIDAPIView.as_view(), name='check_fide_id'),
    path('send-registration-otp/', SendOTPAPIView.as_view(), name='send_registration_otp'),
    path('register-player/', RegisterPlayerAPIView.as_view(), name='register_player'),
    path("login/", PlayerLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("player-transport-new/", PlayerTransportationAPIView.as_view(), name="player_transport"),
    path("fwc-departmentlist/", DepartmentListAPIView.as_view(), name="fwc-departmentlist"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
    path("forgot-password/", ForgetPasswordAPIView.as_view(), name="forgot-password"),
    path("notifications/", PlayerNotificationListView.as_view(), name="player_notifications"),
    path("contact/", ContactFormView.as_view(), name="contact_form"),
    path("enquiry/", EnquiryCreateOrReplyAPI.as_view(), name="enquiry_form"),
    path("enquiry/list/", PlayerEnquiriesWithConversationsAPI.as_view(), name="player_enquiries_list"),
    path("complaint/", ComplaintListView.as_view(), name="raise_complaint"),
    path("complaint/raise/", RaiseComplaintView.as_view(), name="raise_complaint"),
    path("complaint/edit/", EditComplaintRemarkView.as_view(), name="edit_complaint"),
    path("home-images/", HomeImageDataView.as_view(), name="home_images"),
    path('departure-details/', DepartureDetailsAPIView.as_view(), name='create-departure-details-alt'),
    path('fwc-dept-list/', get_departments, name='fwc-dept-list'),
    path('get-departure-details/', DepartureDetailsAPI.as_view(), name='departure-details'),
    path('save-device-token/', SaveDeviceTokenAPI.as_view(), name='save_device_token'),
    path('save-notification-timestamp/', SaveNotificationReadTimestampAPI.as_view(), name='save_notification_timestamp'),
    path('get-announcements-count/', GetAnnouncementsCountAPI.as_view(), name='get_announcements_count'),
]