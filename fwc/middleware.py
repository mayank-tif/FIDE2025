from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.urls import resolve
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.deprecation import MiddlewareMixin

class SessionCheckByMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Define the views that should be exempt from session checking

        self.exempt_apps = ['RFAPIS','MAppApis']

        self.exempt_views = [
            'login',
            'player_registration',
            # Add more exempt views here
        ]

        self.exempt_urls = [
            'fwcadmin:index',
            'fwcadmin:login',
            'fwcadmin:password_change',
            'fwcadmin:logout',
            'firebase-messaging-sw'
            # Add more if needed
        ]

    def __call__(self, request):
        # Get the name of the currently requested view
        current_app_name = resolve(request.path_info).app_name
        current_view = resolve(request.path_info).view_name
        current_url_name = resolve(request.path_info).url_name
        

        if current_app_name in self.exempt_apps:
            return self.get_response(request)
        
        # Check if the current view is in the exempt_views list
        if current_view in self.exempt_views:
            # Skip session check for exempt views
            return self.get_response(request)
        
        if current_url_name in self.exempt_urls:
            return self.get_response(request)
        
        if request.path.startswith('/fwcadmin/'):
            return self.get_response(request)

        # If the session is not active, redirect to the login page
        if not self.is_session_active(request):
            logout(request)
            return HttpResponseRedirect(reverse('login') + '?msg=expired')


        # If the session is active, continue processing the request
        response = self.get_response(request)
        return response

    def is_session_active(self, request):
        # Check if the user is authenticated and session contains a specific key
        #if request.user.is_authenticated and 'loginid' in request.session:
        if request.session.get('is_active') and 'loginid' in request.session:
            return True
        return False
    

class CustomSessionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.session_middleware = SessionMiddleware(get_response)

    def __call__(self, request):
        # Check if the request path matches the custom admin URL path
        if not request.path.startswith('/fwcadmin/'):  # Adjust to your actual admin URL path
            # If not admin path, process session as usual
            self.session_middleware.process_request(request)

        # Proceed with the rest of the middleware chain
        response = self.get_response(request)

        # Apply the session middleware response process for non-admin paths
        if not request.path.startswith('/fwcadmin/'):
            self.session_middleware.process_response(request, response)

        return response
    
    
class DomainRedirectMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get host (domain)
        host = request.get_host().lower()

        # Check domain and path
        if host == "player.fwc2025.in" and request.path == "/":
            return redirect("/player-registration", permanent=True)

        # Continue normal request handling
        response = self.get_response(request)
        return response
    
    
class RoleBasedAccessMiddleware:
    """Middleware to restrict access based on user role."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Allowed URLs for Role ID 2
        self.allowed_urls_role_2_dep_1 = {
            'complaint_list', 
            'complaint_update',
            'DeptAccFBPlayers',
            'DeptPlayerProfile',
            'login',
            'logout',
        }
        
        # self.allowed_urls_role_2_dept_1_or_2 = {
        #     'DeptAccFBPlayers',
        #     'DeptPlayerProfile',
        #     'complaint_list', 
        #     'complaint_update',
        #     'login',
        #     'logout',
        # }
        
        # Allowed URLs for Role ID 3
        self.allowed_urls_role_2_dept_2 = {
            'roaster_list',
            'add_roaster',
            'edit_roaster',
            'complaint_list', 
            'complaint_update',
            'DeptLogPlayers',
            'mark_player_status',
            'start_transport',
            'end_transport',
            'disable_roaster',
            'login',
            'logout',
        }

    def __call__(self, request):
        """Handle the request and apply role-based restrictions."""
        
        if request.session.get('is_active'):
            role_id = request.session.get('roleid', None)
            dept_id = request.session.get('department', None)
            resolver_match = resolve(request.path_info)
            current_url_name = resolver_match.url_name  
            print("Current URL name:", current_url_name, role_id, dept_id)

            # if role_id == 2:
            #     if dept_id in [1, 2]:
            #         allowed_urls = self.allowed_urls_role_2_dept_1_or_2
            #     else:
            #         allowed_urls = self.allowed_urls_role_2

            #     if current_url_name and current_url_name not in allowed_urls:
            #         return HttpResponseRedirect(reverse('login') + '?msg=Unauthorized')
                
            if role_id == 2 and dept_id == 1 and current_url_name and current_url_name not in self.allowed_urls_role_2_dep_1:
                return HttpResponseRedirect(reverse('login') + '?msg=Unauthorized')
            
            if role_id == 2 and dept_id == 2 and current_url_name and current_url_name not in self.allowed_urls_role_2_dept_2:
                return HttpResponseRedirect(reverse('login') + '?msg=Unauthorized')

        return self.get_response(request)