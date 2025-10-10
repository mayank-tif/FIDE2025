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
     