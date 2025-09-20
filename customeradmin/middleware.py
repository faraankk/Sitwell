from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse

class BlockedUserMiddleware:
   
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
    
        if request.user.is_authenticated:
            if hasattr(request.user, 'is_blocked') and request.user.is_blocked:
                messages.error(request, 'Your account has been blocked. Please contact support.')
                logout(request)
                return redirect('login') 
        
        response = self.get_response(request)
        return response
