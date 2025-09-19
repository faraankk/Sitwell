from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

class OTPRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ['/verify-otp-signup/', '/verify-reset-otp/']:
            if request.method == 'POST':
                # Check rate limiting
                session_key = f"otp_attempts_{request.session.session_key}"
                attempts = request.session.get(session_key, 0)
                
                if attempts >= 5:
                    messages.error(request, 'Too many failed attempts. Please try again later.')
                    return redirect('login')
                
                # Increment attempts on failed OTP
                if 'Invalid OTP' in str(request.POST):
                    request.session[session_key] = attempts + 1
        
        response = self.get_response(request)
        return response
