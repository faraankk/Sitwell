from django.contrib.auth.forms import AuthenticationForm
from django import forms

class CustomAuthenticationForm(AuthenticationForm):
    # Override the username field from the parent form
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200',
        'placeholder': 'Enter your username',
        'autofocus': True  # Automatically focuses this field when the page loads
    }))
    
    # Override the password field from the parent form
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200',
        'placeholder': 'Enter your password'
    }))
