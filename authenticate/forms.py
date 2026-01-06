import os
import re
from django import forms
from django.contrib.auth import get_user_model
from .models import CustomUser, UserAddress, Order
from django.contrib.auth import authenticate
from .utils import is_strong_password, is_valid_full_name
from PIL import Image
import uuid

CustomUser = get_user_model()


# --------------------  SIGN-UP  --------------------
class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        label='Password'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )
    referral_code = forms.CharField(
        max_length=8,
        required=False,
        label="Referral code (optional)",
        widget=forms.TextInput(attrs={'placeholder': 'Referral code (optional)'})
    )

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={
                'placeholder': 'Phone Number',
                'pattern': '[0-9]*',
                'inputmode': 'numeric'
            }),
        }

    # ------------- existing clean methods -------------
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            error = is_valid_full_name(first_name)
            if error:
                raise forms.ValidationError(error)
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if last_name:
            error = is_valid_full_name(last_name)
            if error:
                raise forms.ValidationError(error)
        return last_name

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            phone_number = re.sub(r'[^\d]', '', phone_number)
            if not phone_number.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone_number) < 10 or len(phone_number) > 15:
                raise forms.ValidationError("Phone number must be between 10 and 15 digits.")
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                raise forms.ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if CustomUser.objects.filter(email=email).exists():
                raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            errors = is_strong_password(password1)
            if errors:
                if isinstance(errors, list):
                    raise forms.ValidationError(errors)
                else:
                    raise forms.ValidationError(errors)
        return password1

    def clean_referral_code(self):
        code = self.cleaned_data.get('referral_code')
        if code:
            from customeradmin.models import Referral
            if not Referral.objects.filter(code=code.upper()).exists():
                raise forms.ValidationError("Invalid referral code.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# --------------------  LOGIN  --------------------
class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid email address or password.")
            elif not self.user_cache.is_active:
                raise forms.ValidationError("Your account is not activated.")
            elif getattr(self.user_cache, 'is_blocked', False):
                raise forms.ValidationError("Your account has been blocked. Please contact support.")
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)


# --------------------  OTP  --------------------
class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        label='Enter OTP',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 6-digit OTP',
            'pattern': '[0-9]{6}',
            'title': 'Please enter a 6-digit number'
        })
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        if otp:
            if not otp.isdigit():
                raise forms.ValidationError("OTP must contain only numbers.")
            if len(otp) != 6:
                raise forms.ValidationError("OTP must be exactly 6 digits.")
        return otp


# --------------------  NEW PASSWORD  --------------------
class NewPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'New Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password'}))

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            errors = is_strong_password(password)
            if errors:
                if isinstance(errors, list):
                    raise forms.ValidationError(errors)
                else:
                    raise forms.ValidationError(errors)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm_password = cleaned.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


# --------------------  FORGOT PASSWORD  --------------------
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                user = CustomUser.objects.get(email=email)
                if getattr(user, 'is_blocked', False):
                    raise forms.ValidationError("This account has been blocked. Please contact support.")
            except CustomUser.DoesNotExist:
                raise forms.ValidationError("No account found with this email address.")
        return email


# --------------------  PROFILE  --------------------
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone_number', 'date_of_birth', 'bio', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'inputmode': 'numeric'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about yourself...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            error = is_valid_full_name(first_name)
            if error:
                raise forms.ValidationError(error)
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if last_name:
            error = is_valid_full_name(last_name)
            if error:
                raise forms.ValidationError(error)
        return last_name

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            phone_number = re.sub(r'[^\d]', '', phone_number)
            if not phone_number.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone_number) < 10 or len(phone_number) > 15:
                raise forms.ValidationError("Phone number must be between 10 and 15 digits.")
            if CustomUser.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large. Maximum size is 5MB.")
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Invalid image format. Please use JPG, PNG, or GIF.")
        return image


# --------------------  EMAIL CHANGE  --------------------
class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label='New Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter new email address'})
    )
    password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your current password'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')
        if new_email:
            if new_email == self.user.email:
                raise forms.ValidationError("New email must be different from current email.")
            if CustomUser.objects.filter(email=new_email).exists():
                raise forms.ValidationError("A user with this email already exists.")
        return new_email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and not self.user.check_password(password):
            raise forms.ValidationError("Current password is incorrect.")
        return password


# --------------------  PASSWORD CHANGE  --------------------
class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password'})
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'})
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if current_password and not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            errors = is_strong_password(new_password)
            if errors:
                if isinstance(errors, list):
                    raise forms.ValidationError(errors)
                else:
                    raise forms.ValidationError(errors)
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        current_password = cleaned_data.get('current_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("New passwords don't match.")
            if current_password and new_password == current_password:
                raise forms.ValidationError("New password must be different from current password.")
        return cleaned_data


# --------------------  ADDRESS  --------------------
class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = [
            'address_type', 'full_name', 'phone_number', 'address_line_1',
            'address_line_2', 'city', 'state', 'postal_code', 'country', 'is_default'
        ]
        widgets = {
            'address_type': forms.Select(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'inputmode': 'numeric'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2 (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            phone_number = re.sub(r'[^\d]', '', phone_number)
            if not phone_number.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone_number) < 10 or len(phone_number) > 15:
                raise forms.ValidationError("Phone number must be between 10 and 15 digits.")
        return phone_number


# --------------------  ORDER  --------------------
class OrderCancellationForm(forms.Form):
    reason = forms.ChoiceField(
        choices=[
            ('', 'No reason (optional)'),
            ('changed_mind', 'Changed my mind'),
            ('wrong_item', 'Wrong item ordered'),
            ('other', 'Other'),
        ],
        widget=forms.RadioSelect,
        required=False
    )
    additional_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Additional notes (optional)', 'class': 'form-control'}),
        required=False
    )


class OrderReturnForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide the reason for return'}),
        required=True
    )


# --------------------  COUPON  --------------------
class CouponApplyForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter coupon code',
            'class': 'form-control'
        })
    )