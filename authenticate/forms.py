from django import forms
from django.contrib.auth import get_user_model
from .models import CustomUser
from django.contrib.auth import authenticate
from .utils import is_strong_password, is_valid_full_name, is_valid_phone_number

CustomUser = get_user_model()

class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}), label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}), label='Confirm Password')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
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
            error = is_valid_phone_number(phone_number)
            if error:
                raise forms.ValidationError(error)
            
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
            elif hasattr(self.user_cache, 'is_blocked') and self.user_cache.is_blocked:
                raise forms.ValidationError("Your account has been blocked. Please contact support.")
        return cleaned_data
    
    def get_user(self):
        return getattr(self, 'user_cache', None)

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

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                user = CustomUser.objects.get(email=email)
                if hasattr(user, 'is_blocked') and user.is_blocked:
                    raise forms.ValidationError("This account has been blocked. Please contact support.")
            except CustomUser.DoesNotExist:
                raise forms.ValidationError("No account found with this email address.")
        return email
