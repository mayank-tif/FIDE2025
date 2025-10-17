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
from django.core.files.base import ContentFile
from FWC2025.env_details import *


per_page = 50


class View_platformlogin(TemplateView):

    def get(self, request):
        # Check if user is already logged in
        msg = request.GET.get('msg', None)
        
        if msg == "Unauthorized":
            logout(request)  
        
        if request.session.get('is_active'):
            return redirect("/home")
        
        msg = request.GET.get('msg', None)
        return render(request,"login.html",{'msg': msg, 'site_key': RECAPTCHA_SITE_KEY})
    
    def post(self, request):
        username = request.POST.get('username')
        pswd = request.POST.get('password')
        enc_pswd = str_encrypt(str(pswd))
        pswd = enc_pswd

        try:
            # Get reCAPTCHA response from form
            recaptcha_response = request.POST.get('g-recaptcha-response')

            # Verify reCAPTCHA v3 response with Google
            recaptcha_verify_url = "https://www.google.com/recaptcha/api/siteverify"
            recaptcha_data = {
                'secret': RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            recaptcha_result = requests.post(recaptcha_verify_url, data=recaptcha_data).json()

            # Check reCAPTCHA success and score (Google recommends 0.5+)
            if not recaptcha_result.get("success") or recaptcha_result.get("score", 0) < 0.5:
                return render(request, "index.html", {"message": "reCAPTCHA failed. Please try again.", "status": False, "site_key": RECAPTCHA_SITE_KEY})
            
            if pd.isnull(username) or username == '' or username is None:
                return render(request,"login.html",{'message': 'Username should not be empty..!', "status": False, 'site_key': RECAPTCHA_SITE_KEY})
            if pd.isnull(pswd) or pswd == '' or pswd is None:
                return render(request,"login.html",{'message': 'Password should not be empty..!', "status": False, 'site_key': RECAPTCHA_SITE_KEY})
            
            if username is not None and pswd is not None:
                user_dtls = MstUserLogins.objects.filter(loginname=username, securepassword=pswd,status_flag=1)

                if len(user_dtls) > 0:
                    request.session['loginid'] = user_dtls[0].id
                    request.session['loginname'] = user_dtls[0].loginname
                    request.session['roleid'] = user_dtls[0].roleid.id if user_dtls[0].roleid else None
                    request.session['department'] = user_dtls[0].department.id if user_dtls[0].department else None
                    request.session['is_active'] = True
                    request.session['loggedin_user_name'] = user_dtls[0].name
                    request.session['loggedin_user_email'] = user_dtls[0].email
                    log_user_activity(request, "Login", f"User '{username}' logged in successfully")
                    if user_dtls[0].roleid.id == 2:
                        return redirect("/complaints")
                    elif user_dtls[0].roleid.id == 3:
                        return redirect("roaster_list")
                    return redirect("/home")
                else:
                    return render(request,"login.html",{"message": "Incorrect Password!!", "status": False, 'site_key': RECAPTCHA_SITE_KEY})
            else:
                return render(request,"login.html",{"message": "Please provide both username and password", "status": False, 'site_key': RECAPTCHA_SITE_KEY})
        except Exception as e:
            return render(request,"login.html",{"message": "Please provide both username and password ({e})", "status": False, 'site_key': RECAPTCHA_SITE_KEY})

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
            pending_complaints = PlayerComplaint.objects.filter(status__in=['OPEN', 'IN_PROGRESS'], status_flag=1).count()

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
                is_self_registered=False
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
            player.deactivated_by = request.session.get("loginid")
            player.deactivated_on = timezone.now()
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
        player_documents = PlayerDocument.objects.filter(player=player, status_flag=1)
        
        transportation_details = PlayerTransportationDetails.objects.filter(
            playerId=player, 
        ).select_related('roasterId', 'transportationTypeId').order_by('-travel_date', '-created_on')
        
        return render(request, self.template_name, {
            "player": player, 
            "countries": countries, 
            "TransportationTypes": TransportationTypes,
            "player_documents": player_documents,
            "transportation_details": transportation_details
        })
    
    
class UpdatePlayerProfile(View):
    def post(self, request):
        player_id = request.POST.get("player_id")
        print("request post update profile", request.POST)
        print("request.FILES", request.FILES)
        player = get_object_or_404(Players, id=player_id, status_flag=1)

        fide_id = request.POST.get("fide_id")
        
        # Check if FIDE ID exists in FideIDMst
        if not FideIDMst.objects.filter(fide_id=fide_id).exists():
            return JsonResponse({"success": False, "error": "FIDE ID does not exist."})
        
        # Check if FIDE ID is already assigned to another player
        if Players.objects.filter(fide_id=fide_id).exclude(id=player_id).exists():
            return JsonResponse({"success": False, "error": "This FIDE ID is already registered with another player."})
        
        age = request.POST.get("age")
        if age == '':
            age = None
        else:
            try:
                age = int(age) if age else None
            except (ValueError, TypeError):
                age = None

        # Update player details
        player.name = request.POST.get("name")
        player.fide_id = fide_id
        player.age = age
        player.gender = request.POST.get("gender")
        player.email = request.POST.get("email")
        player.status = request.POST.get("status")
        player.countryid_id = request.POST.get("country")
        player.details = request.POST.get("food_allergies", player.details)
        player.room_cleaning_preference = request.POST.get("room_cleaning_preference", player.room_cleaning_preference)
        player.accompanying_persons = request.POST.get("accompanying_persons", player.accompanying_persons)  # NEW

        # Handle profile picture upload
        if "profile_pic" in request.FILES: 
            player.image = request.FILES["profile_pic"]

        # Handle multiple documents upload - UPDATED
        if "documents" in request.FILES:
            documents = request.FILES.getlist("documents")  # Get all files
            fide_id = player.fide_id
            
            for document in documents:
                original_name = document.name
                new_filename = f"{fide_id}_{original_name}"
                
                # Create PlayerDocument record
                player_doc = PlayerDocument(
                    player=player,
                    reg_document=document,
                    original_filename=original_name,
                    file_size=document.size,
                    document_type='IDENTIFICATION'
                )
                # Rename the file
                player_doc.reg_document.name = new_filename
                player_doc.save()

        # Set update timestamp and user
        player.updated_on = timezone.now()
        player.updated_by = request.session.get("loginid")
        player.save()

        data = {"success": True}
        if player.image:
            data["image_url"] = player.image.url
        
        # Get documents for response
        player_documents = PlayerDocument.objects.filter(player=player, status_flag=1)
        if player_documents.exists():
            data["documents"] = [doc.original_filename for doc in player_documents]

        log_user_activity(request, "Update Player Profile", f"Player '{player.name}' profile updated successfully")
        return JsonResponse(data)
    

class DeletePlayerDocument(View):
    def post(self, request):
        document_id = request.POST.get("document_id")
        try:
            document = PlayerDocument.objects.get(id=document_id, status_flag=1)
            document.status_flag = 0  # Soft delete
            document.save()
            
            return JsonResponse({"success": True, "message": "Document deleted successfully"})
        except PlayerDocument.DoesNotExist:
            return JsonResponse({"success": False, "error": "Document not found"})
    
    
class PlayerTransportView(View):
    
    def get(self, request, player_id, *args, **kwargs):
        try:
            transports = PlayerTransportationDetails.objects.filter(
                playerId_id=player_id, 
            ).select_related('roasterId', 'transportationTypeId').order_by('-travel_date', '-created_on')
            
            data = []
            for t in transports:
                transport_data = {
                    "id": t.id,
                    "pickup_location": t.pickup_location or "Not specified",
                    "drop_location": t.drop_location or "Not specified",
                    "details": t.details or "No details provided",
                    "transportation_type": t.transportationTypeId.id if t.transportationTypeId else None,
                    "transportation_type_name": t.transportationTypeId.Name if t.transportationTypeId else "",
                    "remarks": t.remarks or "No remarks",
                    "status": t.status,
                    "status_display": t.get_status_display(),
                    "travel_date": t.travel_date.strftime("%b %d, %Y %I:%M %p") if t.travel_date else "",
                    "created_on": t.created_on.strftime("%b %d, %Y %I:%M %p"),
                }
                
                # Add roaster details if available
                if t.roasterId:
                    transport_data.update({
                        "vehicle_type": t.roasterId.vechicle_type,
                        "vehicle_number": t.roasterId.vechicle_no,
                        "driver_name": t.roasterId.driver_name,
                        "seats": t.roasterId.number_of_seats,
                        "roaster_id": t.roasterId.id,
                    })
                
                data.append(transport_data)
                
            return JsonResponse(data, safe=False)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        


class ComplaintListView(View):
    """Displays all complaints and their conversation threads with search and pagination"""

    def get(self, request):
        search_query = request.GET.get("q", "")
        selected_department = request.GET.get("department", "")

        role_id = request.session.get("roleid")
        user_dept_id = request.session.get("department")
        print("role_id", role_id, "user_dept_id", user_dept_id)

        log_user_activity(request, "View Complaints", "User viewed complaints list")

        # Base queryset
        complaints_qs = PlayerComplaint.objects.select_related("player", "department").prefetch_related(
            Prefetch(
                "conversations",
                queryset=PlayerComplaintConversation.objects.select_related("sender_player", "sender_user").order_by("-created_on")
            )
        ).order_by("-created_on")

        # Apply department filter based on role
        if role_id == 2 and user_dept_id:
            # Normal department user – see only their department’s data
            complaints_qs = complaints_qs.filter(department_id=user_dept_id)
            selected_department = user_dept_id
        elif role_id == 1:
            # Admin can view all and optionally filter by dropdown
            if selected_department:
                complaints_qs = complaints_qs.filter(department_id=selected_department)

        # Apply search filter
        if search_query:
            complaints_qs = complaints_qs.filter(player__name__icontains=search_query)

        paginator = Paginator(complaints_qs, per_page)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        departments = Department.objects.filter(status_flag=1).order_by("name")

        return render(request, "complaints.html", {
            "complaints": page_obj,
            "search_query": search_query,
            "page_obj": page_obj,
            "departments": departments,
            "selected_department": str(selected_department),
            "role_id": role_id,
        })



class ComplaintUpdateView(View):
    """Handles AJAX updates — status change or adding remarks"""

    def post(self, request, complaint_id):
        complaint = get_object_or_404(PlayerComplaint, id=complaint_id)
        new_status = request.POST.get("status")
        message = request.POST.get("message")
        print("new_status", new_status, "message", message)

        if new_status:
            complaint.status = new_status
            complaint.save()
            log_user_activity(request, "Update Complaint Status", f"Complaint ID({complaint_id}) status updated to {new_status}")
        if message:
            sender = MstUserLogins.objects.get(id=request.session.get("loginid"), status_flag=1)
            PlayerComplaintConversation.objects.create(complaint=complaint, sender_user=sender, message=message)
            log_user_activity(request, "Add Remark", f"Complaint ID({complaint_id}) remark added")
            
        return JsonResponse({"success": True, "message": "Complaint updated successfully."})
    

class AnnouncementListView(View):
    def get(self, request):
        search_query = request.GET.get("q", "")

        announcements = Announcements.objects.select_related("created_by").prefetch_related(
            'recipients__player'
        ).all().order_by("-created_on")
        
        if search_query:
            announcements = announcements.filter(title__icontains=search_query)

        paginator = Paginator(announcements, per_page) 
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        players = Players.objects.filter(status_flag=1).order_by("name")

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
        users = MstUserLogins.objects.filter(status_flag=1).order_by("-created_on")
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
        department = None
        if department_id:
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
        log_user_activity(request, "Fetch Data To Edit User", f"User ID({user_id}) - {user.name} edited")
        return JsonResponse({"success": True, "data": data})
    
    def post(self, request, user_id):
        print("rest", request.POST)
        user = get_object_or_404(MstUserLogins, id=user_id)
        role_id = request.POST.get("edit_role")
        department_id = request.POST.get("edit_department")
        role = MstRole.objects.get(id=role_id)
        department = None
        if department_id: 
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
        log_user_activity(request, "Update User", f"User ID({user_id}) - {user.name} updated")
        return JsonResponse({"success": True, "message": "User updated successfully."})
    
    
class ChangeUserPasswordView(View):
    def post(self, request):
        user_id = request.POST.get("userId")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

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

        logs = UserActivityLog.objects.select_related("user", "user__roleid").all().order_by('-created_on') 
            
        if search:
            logs = logs.filter(
                Q(user__loginname__icontains=search) |
                Q(user__name__icontains=search) |
                Q(user__roleid__role_name__icontains=search) |
                Q(action__icontains=search) |
                Q(description__icontains=search)
            )

        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)

        return render(request, self.template_name, {
            "page_obj": page_obj,
            "search": search,
        })


class PlayerRegistrationView(FormView):
    template_name = "player_registration.html"
    form_class = PlayerRegistrationForm
    success_url = reverse_lazy('player_registration')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        # Save the form data
        try:
            player = form.save()
            messages.success(self.request, 'Registration submitted successfully!')
        except Exception as e:
            messages.error(self.request, f'Error submitting registration: {str(e)}')
        return super().form_valid(form)
    
  
  
class RoasterListView(View):
    template_name = "logistics.html"

    def get(self, request):
        search_query = request.GET.get('search', '')
        page_number = request.GET.get('page', 1)

        roasters = Roaster.objects.filter(status_flag=1).order_by('-created_on')
        if search_query:
            roasters = roasters.filter(
                Q(driver_name__icontains=search_query) |
                Q(playertransportationdetails__playerId__name__icontains=search_query)
            ).distinct()

        # Prefetch related PlayerTransportationDetails
        roasters = roasters.prefetch_related('playertransportationdetails_set')

        # Prepare distinct players for each roaster in Python
        for r in roasters:
            players = r.playertransportationdetails_set.all()
            seen = set()
            distinct_players = []
            for p in players:
                if p.playerId.id not in seen:
                    distinct_players.append(p)
                    seen.add(p.playerId.id)
            r.distinct_players = distinct_players

        paginator = Paginator(roasters, per_page)
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'roasters': page_obj.object_list,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)
  
    
    
class RoasterAddView(View):
    template_name = "add-roaster.html"

    def get(self, request):
        players = Players.objects.filter(status_flag=1).order_by("name")
        transportation_types = TransportationType.objects.filter(status_flag=1)
        current_page = request.GET.get('page', 1)
        return render(request, self.template_name, {
            'players': players,
            'transportation_types': transportation_types,
            'status_choices': PlayerTransportationDetails.STATUS_CHOICES,
            'current_page': current_page
        })

    def post(self, request):
        vehicle_type = request.POST.get('vehicleType')
        vehicle_number = request.POST.get('vehicleNumber')
        number_of_seats = request.POST.get('number_of_seats')
        driver_name = request.POST.get('driverName')
        transportation_type_id = request.POST.get('transportationTypeId')
        status = request.POST.get('status')
        assigned_players = request.POST.getlist('players')
        current_page = request.POST.get('current_page', 1)
        travel_date_str = request.POST.get('travel_date')
        travel_date = datetime.strptime(travel_date_str, "%Y-%m-%d %I:%M %p") if travel_date_str else None


        roaster = Roaster.objects.create(
            vechicle_type=vehicle_type,
            vechicle_no=vehicle_number,
            number_of_seats=number_of_seats,
            driver_name=driver_name,
            transportationTypeId_id=transportation_type_id,
            status_flag=1,
            created_by=request.session.get('user_id'),
        )

        # Create player transport log entries
        for player_id in assigned_players:
            player = Players.objects.get(id=player_id)
            PlayerTransportationDetails.objects.create(
                playerId=player,
                roasterId=roaster,
                status=status,
                travel_date=travel_date,
                transportationTypeId_id=transportation_type_id,
                created_by=request.session.get('user_id')
            )

        messages.success(request, "Roaster and player travel details added successfully!")
        return redirect(f"{reverse('roaster_list')}?page={current_page}")

    

class RoasterEditView(View):
    template_name = "edit-roaster.html"

    def get(self, request, roaster_id):
        roaster = get_object_or_404(Roaster, id=roaster_id)
        players = Players.objects.filter(status_flag=1).order_by("name")
        assigned_player_ids = roaster.playertransportationdetails_set.values_list('playerId__id', flat=True)
        transportation_types = TransportationType.objects.filter(status_flag=1)
        current_page = request.GET.get('page', 1)

        return render(request, self.template_name, {
            'roaster': roaster,
            'players': players,
            'assigned_player_ids': assigned_player_ids,
            'transportation_types': transportation_types,
            'status_choices': PlayerTransportationDetails.STATUS_CHOICES,
            'current_page': current_page
        })

    def post(self, request, roaster_id):
        roaster = get_object_or_404(Roaster, id=roaster_id)
        vehicle_type = request.POST.get('vehicleType')
        vehicle_number = request.POST.get('vehicleNumber')
        number_of_seats = request.POST.get('number_of_seats')
        driver_name = request.POST.get('driverName')
        assigned_players = request.POST.getlist('players')
        current_page = request.POST.get('current_page', 1)
        transportation_type_id = request.POST.get('transportationTypeId')
        status = request.POST.get('status')
        travel_date_str = request.POST.get('travel_date')
        travel_date = datetime.strptime(travel_date_str, "%Y-%m-%d %I:%M %p") if travel_date_str else None

        roaster.vechicle_type = vehicle_type
        roaster.vechicle_no = vehicle_number
        roaster.number_of_seats = number_of_seats
        roaster.driver_name = driver_name
        roaster.transportationTypeId_id = transportation_type_id
        roaster.updated_by = request.session.get('user_id')
        roaster.updated_on = timezone.now()
        roaster.save()

        # Append a new transport log for each selected player
        for player_id in assigned_players:
            player = Players.objects.get(id=player_id)
            PlayerTransportationDetails.objects.create(
                playerId=player,
                roasterId=roaster,
                status=status,
                travel_date=travel_date,
                transportationTypeId_id=transportation_type_id,
                created_by=request.session.get('user_id')
            )

        messages.success(request, "Roaster updated successfully! Player travel logs recorded.")
        return redirect(f"{reverse('roaster_list')}?page={current_page}")
    
    

class EnquiryListView(View):
    template_name = "enquiry.html"
    per_page = 10  # adjust pagination size

    def get(self, request):
        search_query = request.GET.get('search', '')
        page_number = request.GET.get('page', 1)

        # Filter enquiries, include player name if search query exists
        enquiries = EnquiryDetails.objects.filter(status_flag=1).select_related('player').order_by('-created_on')

        if search_query:
            enquiries = enquiries.filter(
                Q(player__name__icontains=search_query) |
                Q(message__icontains=search_query)
            )

        paginator = Paginator(enquiries, self.per_page)
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'enquiries': page_obj.object_list,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)

