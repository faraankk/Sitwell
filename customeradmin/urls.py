from django.contrib import admin
from django.urls import path
from customeradmin import views 

urlpatterns = [
    path('login/', views.login_to_account, name='admin_login'), 
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  
    path('customers/', views.customer_view, name='customer-list'),
]