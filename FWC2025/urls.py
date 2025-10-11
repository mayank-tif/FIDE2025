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

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
