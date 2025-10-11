import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, View
from .models import *
from django.urls import reverse
from django.core.paginator import Paginator
import io
import base64
from django.db.models import Count, Sum, Q, OuterRef, Subquery
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from .helpers import * 
import pandas as pd
import requests
from django.contrib.auth import logout
from django.contrib import messages
from .form import *
import os
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime


per_page = 2


class View_platformlogin(TemplateView):

    def get(self, request):
        # Check if user is already logged in
        if request.session.get('is_active'):
            print("already logged in")
            return redirect("/home")
        msg = request.GET.get('msg', None)
        return render(request,"login.html",{'msg': msg})
    
    def post(self, request):
        print("post")
        username = request.POST.get('username')
        pswd = request.POST.get('password')
        enc_pswd = str_encrypt(str(pswd))
        pswd = enc_pswd
        print("enc_pswd", enc_pswd)
        print("username", username)

        try:
            if pd.isnull(username) or username == '' or username is None:
                return render(request,"login.html",{'message': 'Username should not be empty..!', "status": False})
            if pd.isnull(pswd) or pswd == '' or pswd is None:
                return render(request,"login.html",{'message': 'Password should not be empty..!', "status": False})
            
            if username is not None and pswd is not None:
                user_dtls = MstUserLogins.objects.filter(loginname=username, securepassword=pswd,status_flag=1)

                if len(user_dtls) > 0:
                    request.session['loginid'] = user_dtls[0].id
                    request.session['loginname'] = user_dtls[0].loginname
                    request.session['roleid'] = user_dtls[0].roleid.id
                    request.session['is_active'] = True
                    request.session['loggedin_user_name'] = user_dtls[0].name
                    request.session['loggedin_user_email'] = user_dtls[0].email
                    return redirect("/home")
                else:
                    return render(request,"login.html",{"message": "Incorrect Password!!", "status": False})
            else:
                return render(request,"login.html",{"message": "Please provide both username and password", "status": False})
        except Exception as e:
            return render(request,"login.html",{"message": "Please provide both username and password ({e})", "status": False})

class PlatformLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('login'))
    
    
class Dashboard(TemplateView):
    def get(self, request):
        user_id = request.session.get("loginid")
        role_id = request.session.get("roleid")
        print("Dashboard------------------------------------------------")

        try:
            # Count totals
            # total_categories = CategoryMst.objects.count()
            # total_items = Items.objects.count()
            # total_item_orders = ItemOrders.objects.count()
            # customer_count = Customers.objects.count()

            resp_data = {
                # 'customer_count':customer_count,
                # 'total_item_orders':total_item_orders,
                # 'total_items':total_items,
                # 'total_categories':total_categories
            }

            return render(request,"dashboard.html",resp_data)
        except Exception as e:
                return render(request,"dashboard.html",{"message": "No data available  ({e})", "status": True})
            
            
     
class PlayerView(View):
    template_name = "players.html"

    def get(self, request):
        """
        Render player management page with countries list for dropdown.
        """
        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        
        return render(request, self.template_name, {"countries": countries, "MstUserLogins": MstUserLogins})

    def post(self, request):
        """
        Handle AJAX requests:
        - If 'action' == 'fetch' → return paginated players
        - If 'action' == 'add' → create new player
        - If 'action' == 'edit' → update existing player
        """
        action = request.POST.get("action")
        print("action------------------", action)

        if action == "fetch":
            return self.fetch_players(request)
        elif action == "add":
            return self.add_player(request)
        elif action == "edit":
            return self.edit_player(request)
        elif action == "get-player-details":
            return self.get_player_details(request)
        elif action == "delete":                   
            return self.delete_player(request)
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    def fetch_players(self, request):
        """
        Return paginated list of players in JSON.
        """
        page = int(request.POST.get("page", 1))

        # Filter only players
        players = Players.objects.filter(status_flag=1).order_by("-id")

        paginator = Paginator(players, per_page)
        current_page = paginator.get_page(page)

        player_data = [
            {
                "id": player.id,
                "image_url": player.image.url if player.image else "" ,
                "name": f"{player.name}",
                "age": getattr(player, "age", None),
                "gender": getattr(player, "gender", None),
                "country": player.countryid.country_name if player.countryid else "",
                "email": player.email,
                "status": player.get_status_display() if player.status else "",
            }
            for player in current_page
        ]

        pagination = {
            "current_page": current_page.number,
            "total_pages": paginator.num_pages,
            "has_next": current_page.has_next(),
            "has_prev": current_page.has_previous(),
            "page_list": list(paginator.get_elided_page_range(number=current_page.number)),
            "per_page": per_page,
        }

        return JsonResponse({"data": player_data, "pagination": pagination})

    def add_player(self, request):
        """
        Add a new player record.
        """
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            age = request.POST.get("age")
            gender = request.POST.get("gender")
            fide_id = request.POST.get("fideId")
            country_id = request.POST.get("country")

            player = Players.objects.create(
                name=name,
                email=email,
                fide_id=fide_id,
                age=age,
                gender=gender,
                created_by=request.session.get("loginid"),
                created_on=timezone.now(),
                status_flag=1,
                countryid_id=country_id,
            )

            return JsonResponse({"success": True, "message": "Player added successfully"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def edit_player(self, request):
        """
        Update an existing player.
        """
        try:
            player_id = request.POST.get("id")
            player = get_object_or_404(Players, id=player_id)
            country = CountryMst.objects.get(country_id=request.POST.get("country"), status_flag=1)

            player.name = request.POST.get("name")
            player.email = request.POST.get("email")
            player.gender = request.POST.get("gender")
            player.countryid_id = country
            player.age = request.POST.get("age")
            player.fide_id = request.POST.get("fideId")
            player.updated_on = timezone.now()
            player.updated_by = request.session.get("loginid")
            player.status = request.POST.get("status")
            player.save()

            return JsonResponse({"success": True, "message": "Player updated successfully"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
        
    def get_player_details(self, request):
        """
        Fetch details of a specific player for editing.
        """
        player_id = request.POST.get("playerId")
        try:
            player = Players.objects.get(id=player_id, status_flag=1)
            data = {
                "id": player.id,
                "name": player.name,
                "email": player.email,
                "age": player.age,
                "gender": player.gender,
                "country": player.countryid_id,
                "fideId": player.fide_id,
                "status": player.status
            }
            return JsonResponse({"success": True, "data": data})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "error": "Player not found"})

    def delete_player(self, request):
        """
        Soft delete (set status_flag = 0)
        """
        player_id = request.POST.get("id")
        try:
            player = Players.objects.get(id=player_id)
            player.status_flag = 0
            player.updated_on = timezone.now()
            player.updated_by = request.session.get("loginid")
            player.save()
            return JsonResponse({"success": True, "message": "Player deleted successfully"})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "error": "Player not found"})
        
        
        
class PlayerProfile(View):
    template_name = "player-profile.html"

    def get(self, request, player_id):
        player = get_object_or_404(Players, id=player_id, status_flag=1)
        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        print("status", player.status)
        return render(request, self.template_name, {"player": player, "countries": countries})
    
    
class UpdatePlayerProfile(View):
    def post(self, request):
        player_id = request.POST.get("player_id")
        player = get_object_or_404(Players, id=player_id, status_flag=1)

        player.name = request.POST.get("name")
        player.age = request.POST.get("age")
        player.gender = request.POST.get("gender")
        player.email = request.POST.get("email")
        player.status = request.POST.get("status")
        player.countryid_id = request.POST.get("country")

        if "profile_pic" in request.FILES:
            player.image = request.FILES["profile_pic"]

        player.save()

        data = {"success": True}
        if player.image:
            data["profile_pic_url"] = player.image.url

        return JsonResponse(data)