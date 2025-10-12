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
from django.db.models import Prefetch
from django.views.generic.edit import FormView
from django.urls import reverse_lazy


per_page = 50


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
                print("user_dtls", user_dtls)

                if len(user_dtls) > 0:
                    log_user_activity(request, "Login", f"User '{username}' logged in successfully")
                    request.session['loginid'] = user_dtls[0].id
                    request.session['loginname'] = user_dtls[0].loginname
                    request.session['roleid'] = user_dtls[0].roleid.id if user_dtls[0].roleid else None
                    request.session['department'] = user_dtls[0].department.id if user_dtls[0].department else None
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
    def post(self, request):
        log_user_activity(request, "Logout", f"User '{request.session.get('loginname')}' logged out successfully")
        logout(request)
        return redirect(reverse('login'))
    
    
class Dashboard(TemplateView):
    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        try:
            # Total players
            total_players = Players.objects.filter(status_flag=1).count()

            # Active players (assuming status_flag=1 is active)
            active_players = Players.objects.filter(status="ACTIVE", status_flag=1).count()

            # Pending complaints (assuming status='Pending')
            pending_complaints = PlayerComplaint.objects.filter(status='OPEN', status_flag=1).count()

            # Total announcements
            total_announcements = Announcements.objects.count()

            context = {
                "total_players": total_players,
                "active_players": active_players,
                "pending_complaints": pending_complaints,
                "total_announcements": total_announcements,
            }

            return render(request, self.template_name, context)

        except Exception as e:
            return render(request, self.template_name, {
                "message": f"No data available ({e})",
                "status": True
            })
            
            
     
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
            log_user_activity(request, "Add Player", f"Player '{name}' added successfully")

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
            log_user_activity(request, "Update Player", f"Player '{player.name}' updated successfully")

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
            log_user_activity(request, "Get Player Details", f"Player '{player.name}' details fetched successfully")
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
            log_user_activity(request, "Delete Player", f"Player '{player.name}' deleted successfully")
            return JsonResponse({"success": True, "message": "Player deleted successfully"})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "error": "Player not found"})
        
        
        
class PlayerProfile(View):
    template_name = "player-profile.html"

    def get(self, request, player_id):
        player = get_object_or_404(Players, id=player_id, status_flag=1)
        countries = CountryMst.objects.filter(status_flag=1).order_by("country_name")
        TransportationTypes = TransportationType.objects.filter(status_flag=1).order_by("Name")
        print("status", player.status)
        return render(request, self.template_name, {
            "player": player, 
            "countries": countries, 
            "TransportationTypes": TransportationTypes})
    
    
class UpdatePlayerProfile(View):
    def post(self, request):
        player_id = request.POST.get("player_id")
        player = get_object_or_404(Players, id=player_id, status_flag=1)
        print("request.POST", request.POST)

        player.name = request.POST.get("name")
        player.fide_id = request.POST.get("fideId")
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
            
        log_user_activity(request, "Update Player Profile", f"Player '{player.name}' profile updated successfully")

        return JsonResponse(data)
    
    
class PlayerTransportView(View):
    
    def get(self, request, player_id, *args, **kwargs):
        transports = PlayerTransportationDetails.objects.filter(playerId_id=player_id)
        data = []
        for t in transports:
            data.append({
                "id": t.id,
                "pickup_location": t.pickup_location,
                "drop_location": t.drop_location,
                "details": t.details,
                "transportation_type": t.transportationTypeId.id,
                "transportation_type_name": t.transportationTypeId.Name,
                "remarks": t.remarks,
                "status": t.status,
                "created_on": t.created_on.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return JsonResponse(data, safe=False)

    def post(self, request, *args, **kwargs):
        """Create or update a transport record"""
        try:
            data = request.POST
            transport_id = data.get("id")
            player_id = data.get("player_id")
            pickup = data.get("pickup_location")
            dropoff = data.get("drop_location")
            details = data.get("details")
            transport_type_id = data.get("transportation_type")
            remarks = data.get("remarks")
            status = data.get("status", PlayerTransportationDetails.STATUS_PENDING)
            player = Players.objects.filter(id=player_id).first()

            # Get TransportationType object
            transport_type_obj = TransportationType.objects.get(id=transport_type_id)

            if transport_id:  # Update existing record
                transport = PlayerTransportationDetails.objects.get(id=transport_id)
                transport.pickup_location = pickup
                transport.drop_location = dropoff
                transport.details = details
                transport.transportationTypeId = transport_type_obj
                transport.remarks = remarks
                transport.status = status
                transport.updated_on = timezone.now()
                transport.updated_by = request.session.get("loginid")
                transport.save()
                log_user_activity(request, "Update Transport", f"Transport ID({transport_id}) updated successfully")
            else:  # Create new
                PlayerTransportationDetails.objects.create(
                    playerId_id=player_id,
                    pickup_location=pickup,
                    drop_location=dropoff,
                    details=details,
                    transportationTypeId=transport_type_obj,
                    remarks=remarks,
                    status=status,
                    created_by=request.session.get("loginid")
                )
                log_user_activity(request, "Create Transport", f"Transport created successfully for Player ID({player_id}), name({player.name})")

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
        


class ComplaintListView(View):
    """Displays all complaints and their conversation threads with search and pagination"""
    def get(self, request):
        search_query = request.GET.get("q", "")
        log_user_activity(request, "View Complaints", f"User viewed complaints list")

        # Prefetch conversations with sender info, ordered latest first
        complaints_qs = PlayerComplaint.objects.select_related("player").prefetch_related(
            Prefetch(
                "conversations",
                queryset=PlayerComplaintConversation.objects.select_related("sender_player", "sender_user").order_by("-created_on")
            )
        ).all().order_by("-created_on")

        # Apply search filter if query exists
        if search_query:
            complaints_qs = complaints_qs.filter(player__name__icontains=search_query)

        # Pagination: 5 complaints per page
        paginator = Paginator(complaints_qs, per_page)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Debug prints
        for c in page_obj:
            print(f"Complaint #{c.id} by player: {c.player.name}")
            for convo in c.conversations.all():
                player_name = convo.sender_player.name if convo.sender_player else None
                user_name = convo.sender_user.name if convo.sender_user else None
                print(f"  Conversation #{convo.id} - Player: {player_name}, User: {user_name}, Message: {convo.message}")

        return render(request, "complaints.html", {
            "complaints": page_obj,
            "search_query": search_query,
            "page_obj": page_obj,
        })


class ComplaintUpdateView(View):
    """Handles AJAX updates — status change or adding remarks"""

    def post(self, request, complaint_id):
        complaint = get_object_or_404(PlayerComplaint, id=complaint_id)
        action = request.POST.get("action")

        if action == "update_status":
            new_status = request.POST.get("status")
            complaint.status = new_status
            complaint.save()
            log_user_activity(request, "Update Complaint Status", f"Complaint ID({complaint_id}) status updated to {new_status}")
            return JsonResponse({"success": True, "message": "Status updated successfully."})

        elif action == "add_remark":
            message = request.POST.get("message")
            sender = MstUserLogins.objects.get(id=request.session.get("loginid"), status_flag=1)
            PlayerComplaintConversation.objects.create(complaint=complaint, sender_user=sender, message=message)
            log_user_activity(request, "Add Remark", f"Complaint ID({complaint_id}) remark added")
            return JsonResponse({"success": True, "message": "Remark added successfully."})

        return JsonResponse({"success": False, "message": "Invalid action."})
    

class AnnouncementListView(View):
    def get(self, request):
        search_query = request.GET.get("q", "")

        announcements = Announcements.objects.select_related("created_by").all().order_by("-created_on")
        if search_query:
            announcements = announcements.filter(title__icontains=search_query)

        paginator = Paginator(announcements, per_page) 
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        players = Players.objects.filter(status_flag=1).order_by("name")  # For dropdown

        return render(request, "announcements.html", {
            "page_obj": page_obj,
            "players": players,
            "search_query": search_query
        })

    def post(self, request):
        """Create new announcement and assign recipients"""
        title = request.POST.get("title")
        details = request.POST.get("details")
        audience_ids = request.POST.getlist("audience")  # list of player IDs
        current_user = request.session.get("loginid")
        print("title", title, "details", details, "audience_ids", audience_ids, "current_user", current_user)   
        logged_user=MstUserLogins.objects.get(id=current_user)

        announcement = Announcements.objects.create(
            title=title,
            details=details,
            created_by=logged_user,
            created_on=timezone.now()
        )

        # Assign recipients
        if "all" in audience_ids:
            recipients = Players.objects.filter(status_flag=1)
        else:
            recipients = Players.objects.filter(id__in=audience_ids)

        # Add recipients in bulk
        AnnouncementRecipients.objects.bulk_create([
            AnnouncementRecipients(announcement=announcement, player=p, sent_on=timezone.now())
            for p in recipients
        ])
        log_user_activity(request, "Create Announcement", f"Announcement '{title}' created successfully")

        return redirect("announcements")  # Redirect back to list
    
    
class ManageUsersView(View):
    template_name = "users.html"

    def get(self, request):
        users = MstUserLogins.objects.filter(status_flag=1).order_by("id")
        roles = MstRole.objects.filter(status_flag=1)  # Active roles
        departments = Department.objects.filter(status_flag=1)  # Active departments
        
        paginator = Paginator(users, per_page) 
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        context = {
            "page_obj": page_obj,
            "roles": roles,
            "departments": departments,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        name = request.POST.get("name")
        loginname = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirmPassword")
        role_id = request.POST.get("role")
        department_id = request.POST.get("department")
        
        existing_user = MstUserLogins.objects.filter(
            Q(loginname__iexact=loginname) | Q(email__iexact=email)
        ).first()

        if existing_user:
            if existing_user.loginname.lower() == loginname.lower():
                return JsonResponse({"success": False, "message": f"Username '{loginname}' already exists."})
            elif existing_user.email.lower() == email.lower():
                return JsonResponse({"success": False, "message": f"Email '{email}' is already registered."})

        # Validate password
        if password != confirm_password:
            return JsonResponse({"success": False, "message": "Passwords do not match."})
        

        # Fetch role and department objects
        role = MstRole.objects.get(id=role_id)
        department = Department.objects.get(id=department_id)
        
        enc_pswd = str_encrypt(str(password))
        pswd = enc_pswd

        # Create user
        user = MstUserLogins.objects.create(
            name=name,
            loginname=loginname,
            securepassword=pswd,
            email=email,
            mobilenumber=phone,
            roleid=role,
            department=department,
        )
        log_user_activity(request, "Add User", f"New user '{loginname}' created")
        
        return JsonResponse({"success": True, "message": "User added successfully."})
    
        
class DeleteUserView(View):
    def post(self, request, user_id):
        user = get_object_or_404(MstUserLogins, id=user_id)
        user.status_flag = 0
        user.updated_on = timezone.now()
        user.updated_by = request.session.get("loginid")
        user.deactivated_by = request.session.get("loginid")
        user.deactivated_on = timezone.now()
        user.save()
        log_user_activity(request, "Delete User", f"User ID({user_id}) - {user.loginname} deleted")
        return JsonResponse({"success": True, "message": "User deleted successfully."})


class EditUserView(View):
    def get(self, request, user_id):
        """Return user data for editing"""
        user = get_object_or_404(MstUserLogins, pk=user_id)
        data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "username": user.loginname,
            "mobilenumber": user.mobilenumber,
            "department": user.department.id if user.department else None,
            "roleid": user.roleid.id if user.roleid else None,
        }
        log_user_activity(request, "Fetch Data To Edit User", f"User ID({user_id}) - {user.loginname} edited")
        return JsonResponse({"success": True, "data": data})
    
    def post(self, request, user_id):
        print("rest", request.POST)
        user = get_object_or_404(MstUserLogins, id=user_id)
        role_id = request.POST.get("edit_role")
        department_id = request.POST.get("edit_department")
        role = MstRole.objects.get(id=role_id)
        department = Department.objects.get(id=department_id)
        
        user.name = request.POST.get("edit_name")
        user.loginname = request.POST.get("edit_username")
        user.email = request.POST.get("edit_email")
        user.mobilenumber = request.POST.get("edit_phone")
        user.roleid = role
        user.department = department
        user.updated_on = timezone.now()
        user.updated_by = request.session.get("edit_loginid")
        user.save()
        log_user_activity(request, "Update User", f"User ID({user_id}) - {user.loginname} updated")
        return JsonResponse({"success": True, "message": "User updated successfully."})
    
    
class ChangeUserPasswordView(View):
    def post(self, request):
        user_id = request.POST.get("userId")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        print("request.POST", request.POST)

        if not new_password or not confirm_password:
            return JsonResponse({"success": False, "message": "Please fill in all fields."})

        if new_password != confirm_password:
            return JsonResponse({"success": False, "message": "Passwords do not match."})

        try:
            user = MstUserLogins.objects.get(id=user_id, status_flag=1)
            enc_pswd = str_encrypt(str(new_password))
            user.securepassword = enc_pswd
            user.save()
            log_user_activity(request, "Change Password", f"User ID({user_id}) - {user.loginname} password changed")
            return JsonResponse({"success": True, "message": "Password updated successfully."})
        except MstUserLogins.DoesNotExist:
            return JsonResponse({"success": False, "message": "User not found."})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Error: {str(e)}"})
        
        
        
class UserActivityLogView(TemplateView):
    template_name = "activity_log.html"

    def get(self, request):
        page = request.GET.get("page", 1)
        search = request.GET.get("search", "")

        logs = UserActivityLog.objects.select_related("user").all().order_by('-created_on') 

        if search:
            logs = logs.filter(
                Q(user__loginname__icontains=search) |
                Q(user__name__icontains=search) |
                Q(action__icontains=search) |
                Q(description__icontains=search)
            )

        paginator = Paginator(logs, 3)
        page_obj = paginator.get_page(page)

        return render(request, self.template_name, {
            "page_obj": page_obj,
            "search": search,
        })


class PlayerRegistrationView(FormView):
    template_name = "player_registration.html"
    form_class = PlayerRegistrationForm
    success_url = reverse_lazy('player_registration')
    
    def form_valid(self, form):
        # Save the form data
        try:
            player = form.save()
            messages.success(self.request, 'Registration submitted successfully!')
        except Exception as e:
            messages.error(self.request, f'Error submitting registration: {str(e)}')
        return super().form_valid(form)