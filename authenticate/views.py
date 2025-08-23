from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import SignUpForm, OTPForm, NewPasswordForm, LoginForm, ForgotPasswordForm
from .models import CustomUser
from .utils import generate_otp, send_otp_email
import random
import string
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


logger = logging.getLogger(__name__)

# ---------- 1. Sign-up ----------
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.is_active = False  # User is inactive until OTP is verified
                user.otp = generate_otp()
                user.otp_created_at = timezone.now()
                user.save()
                send_otp_email(user.email, user.otp)
                request.session['otp_user_id'] = user.id
                messages.success(request, 'OTP sent to your email.')
                return redirect('verify_otp_signup')
            except Exception as e:
                logger.error(f"Error during signup: {e}")
                messages.error(request, 'An error occurred during signup.')
        else:
            messages.error(request, 'Form is not valid.')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

# ---------- 2. OTP after sign-up ----------
def verify_otp_signup_view(request):
    logger.info("OTP verification view accessed")
    if request.method == 'POST':
        otp = request.POST.get('otp')
        user_id = request.session.get('otp_user_id')
        logger.info(f"Received OTP: {otp}, User ID: {user_id}")
        if user_id and otp:
            try:
                user = CustomUser.objects.get(pk=user_id)
                if otp == user.otp and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    user.is_active = True
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    request.session.pop('otp_user_id', None)
                    messages.success(request, 'Account verified. Please log in.')
                    return redirect('login')  # Redirect to login page
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except CustomUser.DoesNotExist:
                logger.error("User not found")
                messages.error(request, 'User not found.')
        else:
            logger.error("Invalid OTP or user session expired")
            messages.error(request, 'Invalid OTP or user session expired.')
    return render(request, 'verify_otp.html')
# ---------- 3. Log-in ----------
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'You have been successfully logged in.')
                    return redirect('dummy_home') # Redirect to the dummy home page
                else:
                    messages.error(request, 'Your account is disabled.')
            else:
                messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
        
    return render(request, 'login.html', {'form': form})
# ---------- 4. Forgot password ----------
def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                user.otp = generate_otp()  # Generate a new OTP
                user.otp_created_at = timezone.now()
                user.save()
                send_otp_email(user.email, user.otp)  # Send the new OTP
                request.session['reset_user_id'] = user.id  # Save user ID in session
                messages.success(request, 'OTP sent to your email.')
                return redirect('verify_otp_forgot')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Email not found.')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = ForgotPasswordForm()
    return render(request, 'forgot_password.html', {'form': form})

# ---------- 5. OTP for forgot ----------
def verify_otp_forgot_view(request):
    logger.info("OTP verification view accessed")

    # --- Handle Resend ---
    if request.method == 'GET':
        user_id = request.GET.get('resend')
        if user_id:
            try:
                user = CustomUser.objects.get(pk=user_id)
                user.otp = generate_otp()
                user.otp_created_at = timezone.now()
                user.save()
                send_otp_email(user.email, user.otp)
                request.session['reset_user_id'] = user.id  # Save user ID in session
                messages.success(request, 'A new OTP has been sent to your email.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')

    # --- Handle POST (OTP Verification) ---
    if request.method == 'POST':
        otp = request.POST.get('otp')
        user_id = request.session.get('reset_user_id')
        logger.info(f"Received OTP: {otp}, User ID: {user_id}")
        if user_id and otp:
            try:
                user = CustomUser.objects.get(pk=user_id)
                if otp == user.otp and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    request.session['verified_user_id'] = user.id  # Allow password reset
                    request.session.pop('reset_user_id', None)
                    messages.success(request, 'OTP verified. You can now reset your password.')
                    return redirect('new_password')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')
        else:
            messages.error(request, 'Invalid OTP or session expired.')

    return render(request, 'verify_otp.html')

# ---------- 6. New password ----------
def new_password_view(request):
    user_id = request.session.get('verified_user_id')
    if not user_id:
        return redirect('login')
    user = CustomUser.objects.get(pk=user_id)

    if request.method == 'POST':
        form = NewPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            request.session.pop('verified_user_id', None)
            messages.success(request, 'Password changed. Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = NewPasswordForm()
    return render(request, 'new_password.html', {'form': form})

# ---------- 7. Dummy home ----------
def home_view(request):
    return render(request, 'home.html')

# ---------- 8. Generate OTP ----------
def generate_otp():
    otp = ''.join(random.choices(string.digits, k=6))
    print(f"Generated OTP: {otp}")
    return otp

# ---------- Send Test Email ----------
def send_test_email(request):
    subject = 'Test Email'
    message = 'This is a test email from your Django application.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = ['recipient_email@example.com']
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    return HttpResponse('Test email sent')


def logout_view(request):
    logout(request)
    # The logout function handles the redirection if LOGOUT_REDIRECT_URL is set
    return redirect(settings.LOGOUT_REDIRECT_URL)

@login_required
def dummy_home_view(request):
    return render(request, 'dummy.html')