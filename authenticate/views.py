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
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError



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

# ---------- 2. OTP after sign-up  ----------
def verify_otp_signup_view(request):
    logger.info("Sign-up OTP verification view accessed")
    user_id_from_session = request.session.get('otp_user_id')

    # --- Handle Resend (GET request) ---
    if request.method == 'GET':
        resend_user_id = request.GET.get('resend')
        if resend_user_id:
            try:
                if int(resend_user_id) == user_id_from_session:
                    user = CustomUser.objects.get(pk=resend_user_id)
                    user.otp = generate_otp()
                    user.otp_created_at = timezone.now()
                    user.save()
                    send_otp_email(user.email, user.otp)
                    messages.success(request, 'A new OTP has been sent to your email.')
                else:
                    messages.error(request, 'Invalid resend request.')
            except (CustomUser.DoesNotExist, ValueError):
                messages.error(request, 'User not found for resending OTP.')
            return redirect('verify_otp_signup')

    # --- Handle OTP Submission (POST request) ---
    if request.method == 'POST':
        otp = request.POST.get('otp')
        logger.info(f"Received OTP: {otp}, User ID: {user_id_from_session}")
        if user_id_from_session and otp:
            try:
                user = CustomUser.objects.get(pk=user_id_from_session)
                if otp == user.otp and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    user.is_active = True
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    request.session.pop('otp_user_id', None)
                    messages.success(request, 'Account verified. Please log in.')
                    return redirect('login')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except CustomUser.DoesNotExist:
                logger.error("User not found")
                messages.error(request, 'User not found.')
        else:
            logger.error("Invalid OTP or user session expired")
            messages.error(request, 'Invalid OTP or user session expired.')
    
    context = {
        'form_action_url': 'verify_otp_signup',
        'user_id_for_resend': user_id_from_session,
    }
    return render(request, 'verify_otp.html', context)

# ---------- 3. Log-in  ----------
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

# ---------- 4. Forgot password  ----------
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
                return redirect('verify_reset_otp')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Email not found.')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = ForgotPasswordForm()
    return render(request, 'password/forgot_password.html', {'form': form})

# ---------- 5. OTP for forgot password  ----------
def verify_otp_forgot_view(request):
    logger.info("Forgot Password OTP verification view accessed")
    user_id_from_session = request.session.get('reset_user_id')

    # --- Handle Resend (GET request) ---
    if request.method == 'GET':
        resend_user_id = request.GET.get('resend')
        if resend_user_id:
            try:
                if int(resend_user_id) == user_id_from_session:
                    user = CustomUser.objects.get(pk=resend_user_id)
                    user.otp = generate_otp()
                    user.otp_created_at = timezone.now()
                    user.save()
                    send_otp_email(user.email, user.otp)
                    messages.success(request, 'A new OTP has been sent to your email.')
                else:
                    messages.error(request, 'Invalid resend request.')
            except (CustomUser.DoesNotExist, ValueError):
                messages.error(request, 'User not found for resending OTP.')
            return redirect('verify_otp_forgot')

    # --- Handle OTP Submission (POST request) ---
    if request.method == 'POST':
        otp = request.POST.get('otp')
        logger.info(f"Received OTP: {otp}, User ID: {user_id_from_session}")
        if user_id_from_session and otp:
            try:
                user = CustomUser.objects.get(pk=user_id_from_session)
                if otp == user.otp and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    request.session['verified_user_id'] = user.id
                    request.session.pop('reset_user_id', None)
                    messages.success(request, 'OTP verified. You can now reset your password.')
                    return redirect('confi_new_password')  # ← Change to this
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')
        else:
            messages.error(request, 'Invalid OTP or session expired.')

    context = {
        'form_action_url': 'verify_otp_forgot',
        'user_id_for_resend': user_id_from_session,
    }
    return render(request, 'verify_otp.html', context)

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
    return redirect(settings.LOGOUT_REDIRECT_URL)

@login_required
def dummy_home_view(request):
    return render(request, 'dummy.html')




def verify_reset_otp_view(request):
    """
    Displayed after forgot-password form.
    POST only – verifies the OTP and lets the user reset the password.
    """
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please start over.')
        return redirect('forgot_password')

    if request.method == 'POST':
        otp = request.POST.get('otp')
        try:
            user = CustomUser.objects.get(pk=user_id, otp=otp)
            if timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                # success
                user.otp = None
                user.otp_created_at = None
                user.save()
                request.session['verified_user_id'] = user.id
                request.session.pop('reset_user_id', None)
                messages.success(request, 'OTP verified. Create a new password.')
                return redirect('confi_new_password')  # ← Change this line
            else:
                messages.error(request, 'OTP has expired.')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Invalid OTP.')

    return render(request, 'verify_reset_otp.html')




def confirm_new_password_view(request):
    logger.info("Confirm new password view accessed")
    
    # Check if user has verified OTP (session should contain verified_user_id)
    verified_user_id = request.session.get('verified_user_id')
    if not verified_user_id:
        messages.error(request, 'Session expired. Please start the password reset process again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords
        if not new_password or not confirm_password:
            messages.error(request, 'Both password fields are required.')
            return render(request, 'confi_new_password.html')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'confi_new_password.html')
        
        # Use Django's built-in password validation
        try:
            validate_password(new_password)
        except ValidationError as e:
            for error in e:
                messages.error(request, error)
            return render(request, 'confi_new_password.html')
        
        try:
            # Get the user and update password
            user = CustomUser.objects.get(pk=verified_user_id)
            user.set_password(new_password)  # This hashes the password
            user.save()
            
            # Clear the session
            request.session.pop('verified_user_id', None)
            
            messages.success(request, 'Password reset successfully! You can now login with your new password.')
            logger.info(f"Password reset successful for user ID: {verified_user_id}")
            
            return redirect('login')
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found. Please start the password reset process again.')
            return redirect('forgot_password')
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            messages.error(request, 'An error occurred while resetting your password. Please try again.')
            return render(request, 'confi_new_password.html')
    
    # GET request - render the form
    return render(request, 'confi_new_password.html')