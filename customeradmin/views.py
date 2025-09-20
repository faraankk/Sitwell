from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.core.paginator import Paginator
from django.db.models import Q
import logging
from .forms import CustomAuthenticationForm, ProductForm, ProductImageFormSet  
from .models import Product, ProductImage, Category  
from .utils import process_image
from django.db import transaction
from django.db.models import Q, Max  
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model


logger = logging.getLogger(__name__)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_to_account(request):
    if request.user.is_authenticated and request.user.is_superuser:
        print("User is authenticated and superuser, redirecting to admin_dashboard")
        return redirect('admin_dashboard')
    if request.method == 'POST':
        print("POST data received:", request.POST)  
        form = CustomAuthenticationForm(data=request.POST)
        print("Form is valid:", form.is_valid())  
        
        if form.is_valid():
            user = form.get_user()
            print("User found:", user.email, "Is superuser:", user.is_superuser)
            
            if not user.is_superuser:
                messages.error(request, 'Only admin users can log in here.')
                print("User is not a superuser")
                return render(request, 'admin_login.html', {'form': form})
            
            login(request, user)
            username = user.first_name.title() if user.first_name else user.username
            messages.success(request, f"Login Successful. Welcome, {username}!")
            print("Login successful, redirecting to admin_dashboard")
            return redirect('admin_dashboard')
        else:
            print("Form errors:", form.errors)  
            messages.error(request, 'Invalid username or password. Please try again.')
            print("Invalid form data")
            return render(request, 'admin_login.html', {'form': form})
    
    form = CustomAuthenticationForm()
    return render(request, 'admin_login.html', {'form': form})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')

    total_products = Product.objects.count()
    published_products = Product.objects.filter(status='published').count()
    low_stock_products = Product.objects.filter(status='low-stock').count()
    draft_products = Product.objects.filter(status='draft').count()
    
    context = {
        'total_products': total_products,
        'published_products': published_products,
        'low_stock_products': low_stock_products,
        'draft_products': draft_products,
    }
    
    print("Rendering admin_dashboard.html")
    return render(request, 'admin_dashboard.html', context)


@login_required
def customer_view(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('/')
    
    return render(request, 'customers/customer_list.html')


@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def product_view(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    products = Product.objects.all().order_by('-created_at')
    
   
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'out-of-stock':
        products = products.filter(Q(status='out-of-stock') | Q(stock_quantity=0))
    elif status_filter and status_filter != 'all' and status_filter != '':
        products = products.filter(status=status_filter)
    
    
    print(f"Products count after filtering: {products.count()}")
    print(f"Status filter applied: {status_filter}")
    
    paginator = Paginator(products, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'products/product_list.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'current_status': status_filter,
        'status_choices': Product.STATUS_CHOICES,
        'total_products': products.count(),
    })




@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_product(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    if request.method == 'POST':
        print("=== ADD PRODUCT WITH MULTIPLE IMAGES DEBUG ===")
        form = ProductForm(request.POST)
        
        
        images = request.FILES.getlist('images')
        print(f"Number of images received: {len(images)}")

        if request.method == 'POST':
            print("=== DEBUGGING FORM SUBMISSION ===")
            print(f"POST data keys: {list(request.POST.keys())}")
            print(f"FILES data keys: {list(request.FILES.keys())}")
            print(f"All FILES: {request.FILES}")
            print(f"Images from getlist: {request.FILES.getlist('images')}")
            print("=====================================")
    

        
        
        if len(images) < 3:
            messages.error(request, "Please upload at least 3 images for the product.")
            return render(request, 'products/add_product.html', {'form': form})
        
        if len(images) > 6:
            messages.error(request, "Maximum 6 images allowed per product.")
            return render(request, 'products/add_product.html', {'form': form})
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    print(f"Product saved: {product.id} - {product.name}")
                    
                   
                    for index, image in enumerate(images):
                        
                        processed_image = process_image(image)
                        
                        
                        product_image = ProductImage(
                            product=product,
                            image=processed_image,
                            is_primary=(index == 0),  
                            order=index
                        )
                        product_image.save()
                        print(f"Image {index + 1} saved for product {product.name}")
                    
                    messages.success(request, f"Product '{product.name}' with {len(images)} images added successfully!")
                    return redirect('product-list')
                    
            except Exception as e:
                error_msg = f"Error saving product: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                messages.error(request, error_msg)
        else:
            
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        print("===========================================")
    else:
        form = ProductForm()
    
    return render(request, 'products/add_product.html', {'form': form})


@login_required
def edit_product(request, product_id):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        
       
        new_images = request.FILES.getlist('images')
        existing_images_count = product.images.count()
        total_images = existing_images_count + len(new_images)
        
        print(f"=== EDIT PRODUCT DEBUG ===")
        print(f"Existing images: {existing_images_count}")
        print(f"New images: {len(new_images)}")
        print(f"Total images: {total_images}")
        
        
        if total_images < 3:
            messages.error(request, f"Product must have at least 3 images. Currently has {existing_images_count}. Please upload {3 - existing_images_count} more images.")
            existing_images = product.images.all().order_by('order')
            images_count = existing_images.count()
            images_remaining = 6 - images_count
            return render(request, 'products/edit_product.html', {
                'form': form, 
                'product': product,
                'existing_images': existing_images,
                'images_count': images_count,
                'images_remaining': images_remaining,
                'min_images_required': max(0, 3 - images_count),
            })
        
        if total_images > 6:
            messages.error(request, "Maximum 6 images allowed per product.")
            existing_images = product.images.all().order_by('order')
            images_count = existing_images.count()
            images_remaining = 6 - images_count
            return render(request, 'products/edit_product.html', {
                'form': form, 
                'product': product,
                'existing_images': existing_images,
                'images_count': images_count,
                'images_remaining': images_remaining,
                'min_images_required': max(0, 3 - images_count),
            })
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    
                    updated_product = form.save()
                    
                    
                    if new_images:
                        current_max_order = product.images.aggregate(max_order=Max('order'))['max_order'] or -1
                        
                        for index, image in enumerate(new_images):
                           
                            if image.size > 5 * 1024 * 1024:  
                                messages.warning(request, f"Image '{image.name}' is too large (max 5MB). Skipped.")
                                continue
                            
                            if not image.content_type.startswith('image/'):
                                messages.warning(request, f"'{image.name}' is not a valid image. Skipped.")
                                continue
                            
                            processed_image = process_image(image)
                            
                            product_image = ProductImage(
                                product=product,
                                image=processed_image,
                                is_primary=False,  
                                order=current_max_order + index + 1
                            )
                            product_image.save()
                            print(f"New image {index + 1} added to product {product.name}")
                    
                    messages.success(request, f"Product '{updated_product.name}' updated successfully!")
                    return redirect('product-list')
                    
            except Exception as e:
                error_msg = f"Error updating product: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                messages.error(request, error_msg)
        else:
            
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm(instance=product)
    
    existing_images = product.images.all().order_by('order')
    images_count = existing_images.count()
    images_remaining = 6 - images_count
    
    return render(request, 'products/edit_product.html', {
        'form': form, 
        'product': product,
        'existing_images': existing_images,
        'images_count': images_count,
        'images_remaining': images_remaining,
        'min_images_required': max(0, 3 - images_count),
    })


@login_required
@require_POST
def delete_product_image(request, image_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        image = get_object_or_404(ProductImage, id=image_id)
        image.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error deleting product image: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def custom_logout(request):
    """Custom logout view that redirects to admin login"""
    from django.contrib.auth import logout
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been successfully logged out.")
        return redirect('login_to_account')  
    return redirect('login_to_account')




@login_required
@require_POST
def soft_delete_product(request, product_id):
    """Soft delete a product"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        product = get_object_or_404(Product.all_objects, id=product_id)
        
        if product.is_deleted:
            return JsonResponse({'success': False, 'error': 'Product is already deleted'})
        
        deleted_by = request.user.email if hasattr(request.user, 'email') else request.user.username
        product.soft_delete(deleted_by=deleted_by)
        
        return JsonResponse({
            'success': True,
            'message': f"Product '{product.name}' deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error soft deleting product: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def restore_product(request, product_id):
    """Restore a soft-deleted product"""
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('/')
    
    try:
        product = get_object_or_404(Product.all_objects, id=product_id)
        
        if not product.is_deleted:
            messages.warning(request, f"Product '{product.name}' is not deleted.")
            return redirect('product-list')
        
        product.restore()
        messages.success(request, f"Product '{product.name}' has been restored successfully.")
        
    except Exception as e:
        logger.error(f"Error restoring product: {str(e)}")
        messages.error(request, f"Error restoring product: {str(e)}")
    
    return redirect('product-list')

@login_required
def deleted_products_view(request):
    """View to show all soft-deleted products"""
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    deleted_products = Product.all_objects.filter(is_deleted=True).order_by('-deleted_at')
    
    paginator = Paginator(deleted_products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'products/deleted_products.html', {
        'products': page_obj,
        'page_obj': page_obj,
    })

@login_required
@require_POST
def delete_single_image(request, image_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        image = get_object_or_404(ProductImage, id=image_id)
        product = image.product
        
        remaining_images = product.images.exclude(id=image_id).count()
        if remaining_images < 3:
            return JsonResponse({
                'success': False, 
                'error': 'Cannot delete image. Product must have at least 3 images.'
            })
        
        image.delete()
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
    

@login_required
def category_view(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    categories = Category.objects.all().order_by('-created_at')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if request.GET.get('clear'):
        return redirect('category-list')
    
    paginator = Paginator(categories, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'category/category.html', {
        'categories': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    })



@login_required
@require_POST
def add_category(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        name = request.POST.get('name')
        is_listed = request.POST.get('is_listed') == 'true'
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'})
        
        if Category.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'Category already exists'})
        
        category = Category.objects.create(
            name=name,
            is_listed=is_listed
        )
        
        return JsonResponse({'success': True, 'id': category.id, 'message': 'Category created successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def edit_category(request, category_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        category = get_object_or_404(Category, id=category_id)
        
        name = request.POST.get('name')
        is_listed = request.POST.get('is_listed') == 'true'
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'})
        
        category.name = name
        category.is_listed = is_listed
        category.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def soft_delete_category(request, category_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        category = get_object_or_404(Category.all_objects, id=category_id)
        if category.is_deleted:
            return JsonResponse({'success': False, 'error': 'Category is already deleted'})
        
        deleted_by = request.user.email if hasattr(request.user, 'email') else request.user.username
        category.soft_delete(deleted_by=deleted_by)
        
        return JsonResponse({
            'success': True,
            'message': f"Category '{category.name}' deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error soft deleting category: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def restore_category(request, category_id):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('/')
    
    try:
        category = get_object_or_404(Category.all_objects, id=category_id)
        if not category.is_deleted:
            messages.warning(request, f"Category '{category.name}' is not deleted.")
            return redirect('category-list')
        
        category.restore()
        messages.success(request, f"Category '{category.name}' has been restored successfully.")
    except Exception as e:
        logger.error(f"Error restoring category: {str(e)}")
        messages.error(request, f"Error restoring category: {str(e)}")
    
    return redirect('category-list')

@login_required
def deleted_categories_view(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    deleted_categories = Category.all_objects.filter(is_deleted=True).order_by('-deleted_at')
    
    paginator = Paginator(deleted_categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'categories/deleted_categories.html', {  
        'categories': page_obj,
        'page_obj': page_obj,
    })

@login_required
@require_POST 
def toggle_category_listed(request, category_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        category = get_object_or_404(Category, id=category_id)
        category.is_listed = not category.is_listed
        category.save()
        return JsonResponse({'success': True, 'is_listed': category.is_listed})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

@login_required
def deleted_categories_view(request):
    """View to show all soft-deleted categories"""
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('/')
    
    deleted_categories = Category.all_objects.filter(is_deleted=True).order_by('-deleted_at')
    
    paginator = Paginator(deleted_categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'category/deleted_categories.html', {
        'categories': page_obj,
        'page_obj': page_obj,
    })

@login_required
def restore_category(request, category_id):
    """Restore a soft-deleted category"""
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('/')
    
    try:
        category = get_object_or_404(Category.all_objects, id=category_id)
        if not category.is_deleted:
            messages.warning(request, f"Category '{category.name}' is not deleted.")
            return redirect('deleted-categories')
        
        category.restore()
        messages.success(request, f"Category '{category.name}' has been restored successfully.")
        
    except Exception as e:
        logger.error(f"Error restoring category: {str(e)}")
        messages.error(request, f"Error restoring category: {str(e)}")
    
    return redirect('deleted-categories')


'''User Management'''

User = get_user_model()

@login_required
def user_management_view(request):
    """Admin user management with search, pagination, and sorting"""
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('/')
    
    users = User.objects.filter(is_superuser=False).order_by('-created_at')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    if request.GET.get('clear'):
        return redirect('user-management')
    
    paginator = Paginator(users, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'User/user_management.html', {  
    'users': page_obj,
    'page_obj': page_obj,
    'search_query': search_query,
})

@login_required
@require_POST
def block_user(request, user_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        if user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Cannot block superuser'})
        
        if user.is_blocked:
            return JsonResponse({'success': False, 'error': 'User is already blocked'})
        
        
        user.block_user(blocked_by=request.user.email)
        
        
        sessions = Session.objects.all()
        for session in sessions:
            try:
                data = session.get_decoded()
                if str(user.id) == data.get('_auth_user_id'):
                    session.delete()
            except:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'User {user.email} has been blocked and logged out successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def unblock_user(request, user_id):
    """Unblock user with confirmation"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        if not user.is_blocked:
            return JsonResponse({'success': False, 'error': 'User is not blocked'})
        
        user.unblock_user()
        
        return JsonResponse({
            'success': True,
            'message': f'User {user.email} has been unblocked successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

