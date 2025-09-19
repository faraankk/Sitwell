from django.urls import path
from customeradmin import views 

urlpatterns = [
    path('adminlogin/', views.login_to_account, name='login_to_account'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('products/', views.product_view, name='product-list'),
    path('products/add/', views.add_product, name='add-product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit-product'),
    path('products/delete-image/<int:image_id>/', views.delete_product_image, name='delete-product-image'),
    path('products/delete-single-image/<int:image_id>/', views.delete_single_image, name='delete-single-image'),  # NEW
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
    path('categories/deleted/', views.deleted_categories_view, name='deleted-categories'),
    path('categories/restore/<int:category_id>/', views.restore_category, name='restore-category'),
    path('user-management/', views.user_management_view, name='user-management'),
    path('block-user/<int:user_id>/', views.block_user, name='block-user'),
    path('unblock-user/<int:user_id>/', views.unblock_user, name='unblock-user'),

    
]