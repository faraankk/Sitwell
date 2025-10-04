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

    path('contact/', views.contact, name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
    path('about/', views.about, name='about'),
    
    # Profile URLs
    path('profile/', views.user_profile_view, name='user_profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/change-email/', views.change_email_view, name='change_email'),
    path('profile/verify-email-otp/', views.verify_email_otp_view, name='verify_email_otp'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    
    # Address URLs
    path('profile/addresses/', views.manage_addresses_view, name='manage_addresses'),
    path('profile/addresses/add/', views.add_address_view, name='add_address'),
    path('profile/addresses/edit/<int:address_id>/', views.edit_address_view, name='edit_address'),
    path('profile/addresses/delete/<int:address_id>/', views.delete_address_view, name='delete_address'),
    path('profile/addresses/set-default/<int:address_id>/', views.set_default_address_view, name='set_default_address'),
    
    # Cart URLs
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update-quantity/', views.update_cart_quantity_view, name='update_cart_quantity'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart_view, name='clear_cart'),
    path('cart/count/', views.cart_item_count_view, name='cart_item_count'),
    
    # Wishlist URLs (uncomment if implemented)
    # path('wishlist/', views.wishlist_view, name='wishlist'),
    # path('wishlist/add/<int:product_id>/', views.add_to_wishlist_view, name='add_to_wishlist'),
    # path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist_view, name='remove_from_wishlist'),
    
    # Checkout and Order URLs
    path('checkout/', views.checkout_view, name='checkout'),
    path('place-order/', views.place_order_view, name='place_order'),
    path('order-success/<str:order_id>/', views.order_success_view, name='order_success'),
    
    # Order Management URLs
    path('orders/', views.user_orders_view, name='user_orders'),
    path('orders/<str:order_id>/', views.order_detail_view, name='order_detail'),
    path('orders/<str:order_id>/cancel/', views.cancel_order_view, name='cancel_order'),
    path('orders/<str:order_id>/cancel-item/<int:item_id>/', views.cancel_order_view, name='cancel_order_item'),
    path('orders/<str:order_id>/return/', views.return_order_view, name='return_order'),
    path('orders/<str:order_id>/invoice/', views.download_invoice_view, name='download_invoice'),
]