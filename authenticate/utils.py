import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re
from django.contrib.auth.password_validation import CommonPasswordValidator


def generate_otp():
    otp = ''.join(random.choices(string.digits, k=6))
    print(f"Generated OTP: {otp}") 
    return otp


def send_otp_email(email, otp):
    subject = "Sit Well – Your One-Time Password"
    message = f"Hi,\nYour OTP is {otp}. It is valid for 2 minutes.\n\nRegards,\nSit Well"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


def send_otp(email):
    otp = ''.join(random.choices(string.digits, k=6))  
    subject = 'Taste for Tails- Your OTP Code'
    message = f"This is your OTP code from Taste for tails: {otp}. It is valid for 2 minutes."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)
    return otp


def is_strong_password(password):
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must include at least one uppercase letter.")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must include at least one lowercase letter.")
    
    if not re.search(r'\d', password):
        errors.append("Password must include at least one digit.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/]', password):
        errors.append("Password must include at least one special character.")
    
    if re.search(r'(.)\1{2,}', password):
        errors.append("Password cannot contain 3 or more repeated characters.")
    
    sequential_patterns = [
        r'(012|123|234|345|456|567|678|789|890)',
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',
        r'(987|876|765|654|543|432|321|210)'
    ]
    
    for pattern in sequential_patterns:
        if re.search(pattern, password.lower()):
            errors.append("Password cannot contain sequential characters.")
            break
    
    try:
        validate_password(password)
    except ValidationError as e:
        errors.extend(e.messages)
    
    return errors if errors else None


def clean_phone_number(number):
    """Clean phone number by removing all non-digit characters"""
    if not number:
        return number
    return re.sub(r'[^\d]', '', str(number))


def is_valid_phone_number(number):
    """Validate phone number and return cleaned number or error message"""
    if not number:
        return "Phone number is required."
    
    # Clean the number first
    cleaned_number = clean_phone_number(number)
    
    if len(cleaned_number) < 10 or len(cleaned_number) > 15:
        return "Phone number must be between 10 and 15 digits."
    
    if len(set(cleaned_number)) == 1:
        return "Phone number cannot have all identical digits."
    
    fake_patterns = [
        '1234567890', '9876543210', '0123456789',
        '1111111111', '2222222222', '3333333333', '4444444444',
        '5555555555', '6666666666', '7777777777', '8888888888',
        '9999999999', '0000000000'
    ]
    
    if cleaned_number in fake_patterns:
        return "Please enter a valid phone number."
    
    # Return None if valid (no error)
    return None


def format_phone_display(number):
    """Format phone number for display purposes only - NOT for storage"""
    cleaned = clean_phone_number(number)
    if cleaned and len(cleaned) == 10:
        # Only format for display, never store formatted version
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    return cleaned


# Updated name validation
def is_valid_full_name(name):
    """Enhanced name validation supporting various name formats."""
    name = name.strip()
    
    if len(name) < 2:
        return "Name must be at least 2 characters long."
    
    if len(name) > 50:
        return "Name cannot exceed 50 characters."
    
    # Allow letters, spaces, hyphens, apostrophes, and dots
    if not re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)*(?:[-'.] ?[A-Za-z]+)*", name):
        return "Name must contain only letters, spaces, hyphens, apostrophes, and dots."
    
    # Check for excessive spaces
    if '  ' in name:
        return "Name cannot contain multiple consecutive spaces."
    
    return None
