from django.urls import path
from customeradmin import views 

app_name = 'customeradmin'  

urlpatterns = [
    path('adminlogin/', views.login_to_account, name='login_to_account'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('products/', views.product_view, name='product-list'),
    path('products/add/', views.add_product, name='add-product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit-product'),
    path('products/delete-image/<int:image_id>/', views.delete_product_image, name='delete-product-image'),
    path('products/delete-single-image/<int:image_id>/', views.delete_single_image, name='delete-single-image'),  
    path('products/soft-delete/<int:product_id>/', views.soft_delete_product, name='soft-delete-product'),
    path('products/restore/<int:product_id>/', views.restore_product, name='restore-product'),
    path('products/deleted/', views.deleted_products_view, name='deleted-products'),
    path('customers/', views.customer_view, name='customer-list'),
    path('logout/', views.custom_logout, name='admin_logout'),

    
    path('categories/', views.category_view, name='category-list'),
    path('categories/add/', views.add_category, name='add-category'),
    path('categories/edit/<int:category_id>/', views.edit_category, name='edit-category'),
    path('categories/toggle-listed/<int:category_id>/', views.toggle_category_listed, name='toggle-category-listed'),
    path('categories/soft-delete/<int:category_id>/', views.soft_delete_category, name='soft-delete-category'),
    path('categories/restore/<int:category_id>/', views.restore_category, name='restore-category'),
    path('categories/deleted/', views.deleted_categories_view, name='deleted-categories'),  
    
    path('user-management/', views.user_management_view, name='user-management'),
    path('block-user/<int:user_id>/', views.block_user, name='block-user'),
    path('unblock-user/<int:user_id>/', views.unblock_user, name='unblock-user'),


    path("orders/", views.order_list, name="order-list"),
    path("orders/<int:order_id>/", views.order_detail, name="order-detail"),
    path("orders/<int:order_id>/status", views.order_update_status, name="order-update-status"),
    path("orders/<int:order_id>/cancel", views.order_cancel, name="order-cancel"),


    path('admin/verify-return/<str:order_id>/', views.verify_return_request, name='verify_return'),
    path('return-requests/', views.return_requests_list, name='return_requests_list'),

    path('return-requests/<int:return_id>/', views.return_request_detail, name='return_request_detail'),

    path('coupons/', views.coupon_list, name='coupon-list'),
    path('coupons/add/', views.coupon_add,  name='coupon-add'),
    path('coupons/delete/<int:coupon_id>/', views.coupon_delete, name='coupon-delete'),
    path('coupons/edit/<int:coupon_id>/', views.coupon_edit, name='coupon-edit'),
    path('coupons/export/<str:format>/', views.coupon_export, name='coupon-export'),   # optional bonus

    path('reports/sales/', views.sales_report, name='sales-report'),
    path('reports/sales/download/<str:format>/', views.sales_report_download, name='sales-report-download'),

    path('banners/', views.banner_list, name='banner-list'),
    path('banners/add/', views.banner_add, name='banner-add'),
    path('banners/edit/<int:banner_id>/', views.banner_edit, name='banner-edit'),
    path('banners/delete/<int:banner_id>/', views.banner_delete, name='banner-delete'),
]