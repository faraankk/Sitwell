from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp-signup/', views.verify_otp_signup_view, name='verify_otp_signup'),
    path('login/', views.login_view, name='login'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_forgot_view, name='verify_otp_forgot'),
    path('new-password/', views.new_password_view, name='new_password'),
    path('', views.home_view, name='home'),
    path('dummy-home/', views.dummy_home_view, name='dummy_home'), # New URL for the dummy page
    path('logout/', views.logout_view, name='logout'),
]