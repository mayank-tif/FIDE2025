"""
URL configuration for FWC2025 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from fwc.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('fwcadmin/', admin.site.urls),
    path('', View_platformlogin.as_view(),name="login"),
    path('home/', Dashboard.as_view(),name="home"),
    path('logout/', PlatformLogoutView.as_view(),name="logout"),
    path('players/', PlayerView.as_view(), name='players'),
    path('player/<int:player_id>/', PlayerProfile.as_view(), name='PlayerProfile'),
    path('update-player-profile/', UpdatePlayerProfile.as_view(), name='update_player_profile'),
    path('player/<int:player_id>/transport/', PlayerTransportView.as_view(), name='get_player_transport'),
    path('player/transport/save/', PlayerTransportView.as_view(), name='save_player_transport'),
    path('complaints/', ComplaintListView.as_view(), name='complaint_list'),
    path('complaints/<int:complaint_id>/update/', ComplaintUpdateView.as_view(), name='complaint_update'),
    path('announcements/', AnnouncementListView.as_view(), name='announcements'),
    path("manage-users/", ManageUsersView.as_view(), name="manage_users"),
    path('users/delete/<int:user_id>/', DeleteUserView.as_view(), name='delete_user'),
    path('users/edit/<int:user_id>/', EditUserView.as_view(), name='edit_user'),
    path('users/change-password/', ChangeUserPasswordView.as_view(), name='change_user_password'),
    path("activity-log/", UserActivityLogView.as_view(), name="activity_log"),
    path('player-registration/', PlayerRegistrationView.as_view(), name='player_registration'),
    path("logistics/roasters/", RoasterListView.as_view(), name="roaster_list"),
    path('logistics/roasters/add/', RoasterAddView.as_view(), name='add_roaster'),
    path('logistics/roasters/edit/<int:roaster_id>/', RoasterEditView.as_view(), name='edit_roaster'),
    path('delete-player-document/', DeletePlayerDocument.as_view(), name='delete_player_document'),
    path('enquiries/', EnquiryListView.as_view(), name='enquiry_list'),
    path('mapi/', include('MAppApis.urls', namespace='MAppApis')),
    path('dept/players/', DeptPlayerView.as_view(), name='DeptAccFBPlayers'),
    path('dept/player/<int:player_id>/', DeptPlayerProfile.as_view(), name='DeptPlayerProfile'),
    path('dept/log/players/', PlayerLogisticsView.as_view(), name='DeptLogPlayers'),
    path('logistics/roasters/start/<int:roaster_id>/', StartTransportView.as_view(), name='start_transport'),
    path('logistics/roasters/end/<int:roaster_id>/', EndTransportView.as_view(), name='end_transport'),
    path('player-logistics/mark-status/<int:player_id>/', MarkPlayerStatusView.as_view(), name='mark_player_status'),
    path('export-players/', PlayersExportView.as_view(), name='export_players'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
