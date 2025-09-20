# authenticate/urls.py (ADD these lines to your existing URLs)
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp-signup/', views.verify_otp_signup_view, name='verify_otp_signup'),
    path('login/', views.login_view, name='login'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('confi-new-password/', views.confirm_new_password_view, name='confi_new_password'),
    path('', views.home_view, name='home'),
    path('dummy-home/', views.dummy_home_view, name='dummy_home'),
    path('products/', views.product_list_view, name='product_list'),
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-reset-otp/', views.verify_reset_otp_view, name='verify_reset_otp'),
]