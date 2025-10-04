from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse 
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph  
from reportlab.lib.styles import getSampleStyleSheet  
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from .models import Order, OrderItem, OrderStatusHistory, CustomUser, UserAddress, Cart, CartItem, Wishlist, WishlistItem
from .forms import OrderCancellationForm, OrderReturnForm, SignUpForm, OTPForm, NewPasswordForm, LoginForm, ForgotPasswordForm, UserProfileForm, EmailChangeForm, PasswordChangeForm, UserAddressForm
from customeradmin.models import Product, Category, ProductImage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from django.views.decorators.cache import cache_control
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.core.paginator import Paginator
from django.db.models import Sum
from decimal import Decimal
from .utils import generate_otp, send_otp_email
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.is_active = False 
                user.otp = generate_otp()
                user.otp_created_at = timezone.now()
                user.save()
                send_otp_email(user.email, user.otp)
                request.session['otp_user_id'] = user.id
                messages.success(request, 'OTP sent to your email.')
                return redirect('verify_otp_signup')
            except Exception as e:
                logger.error(f"Error during signup: {e}")
                messages.error(request, 'An error occurred during signup.')
        else:
            messages.error(request, 'Form is not valid.')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def verify_otp_signup_view(request):
    user_id_from_session = request.session.get('otp_user_id')
    
    if not user_id_from_session:
        messages.error(request, 'Session expired. Please sign up again.')
        return redirect('signup')

    if request.method == 'GET':
        resend_user_id = request.GET.get('resend')
        if resend_user_id:
            try:
                if int(resend_user_id) == user_id_from_session:
                    user = CustomUser.objects.get(pk=resend_user_id)
                    user.otp = generate_otp()
                    user.otp_created_at = timezone.now()
                    user.save()
                    send_otp_email(user.email, user.otp)
                    messages.success(request, 'New OTP sent successfully!')
                    logger.info(f"OTP resent for user: {user.email}")
                else:
                    messages.error(request, 'Invalid resend request.')
            except (CustomUser.DoesNotExist, ValueError):
                messages.error(request, 'User not found.')
            return redirect('verify_otp_signup')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        logger.info(f"OTP verification attempt: {otp} for user ID: {user_id_from_session}")
        
        if otp and len(otp) == 6:
            try:
                user = CustomUser.objects.get(pk=user_id_from_session)
                
                if user.otp_created_at and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    if otp == user.otp:
                        user.is_active = True
                        user.otp = None
                        user.otp_created_at = None
                        user.save()
                        
                        request.session.pop('otp_user_id', None)
                        
                        messages.success(request, 'Account verified successfully! Please log in.')
                        logger.info(f"User activated: {user.email}")
                        return redirect('login')
                    else:
                        messages.error(request, 'Invalid OTP. Please check and try again.')
                else:
                    messages.error(request, 'OTP has expired. Please request a new one.')
                    
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')
        else:
            messages.error(request, 'Please enter a valid 6-digit OTP.')
    
    try:
        user = CustomUser.objects.get(pk=user_id_from_session)
        if user.otp_created_at:
            elapsed_time = (timezone.now() - user.otp_created_at).total_seconds()
            remaining_time = max(0, 120 - int(elapsed_time))
        else:
            remaining_time = 0
    except CustomUser.DoesNotExist:
        remaining_time = 0
    
    context = {
        'form_action_url': 'verify_otp_signup',
        'user_id_for_resend': user_id_from_session,
        'remaining_time': remaining_time,
    }
    return render(request, 'verify_otp.html', context)

@ensure_csrf_cookie
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dummy_home')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                user.otp = generate_otp()
                user.otp_created_at = timezone.now()
                user.save()
                send_otp_email(user.email, user.otp)
                request.session['reset_user_id'] = user.id
                messages.success(request, 'OTP sent to your email.')
                return redirect('verify_reset_otp')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Email not found.')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = ForgotPasswordForm()
    return render(request, 'password/forgot_password.html', {'form': form})

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def verify_otp_forgot_view(request):
    logger.info("Forgot Password OTP verification view accessed")
    user_id_from_session = request.session.get('reset_user_id')

    if request.method == 'GET':
        resend_user_id = request.GET.get('resend')
        if resend_user_id:
            try:
                if int(resend_user_id) == user_id_from_session:
                    user = CustomUser.objects.get(pk=resend_user_id)
                    user.otp = generate_otp()
                    user.otp_created_at = timezone.now()
                    user.save()
                    send_otp_email(user.email, user.otp)
                    messages.success(request, 'A new OTP has been sent to your email.')
                else:
                    messages.error(request, 'Invalid resend request.')
            except (CustomUser.DoesNotExist, ValueError):
                messages.error(request, 'User not found for resending OTP.')
            return redirect('verify_otp_forgot')

    if request.method == 'POST':
        otp = request.POST.get('otp')
        logger.info(f"Received OTP: {otp}, User ID: {user_id_from_session}")
        if user_id_from_session and otp:
            try:
                user = CustomUser.objects.get(pk=user_id_from_session)
                if otp == user.otp and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    request.session['verified_user_id'] = user.id
                    request.session.pop('reset_user_id', None)
                    messages.success(request, 'OTP verified. You can now reset your password.')
                    return redirect('confi_new_password')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')
        else:
            messages.error(request, 'Invalid OTP or session expired.')

    context = {
        'form_action_url': 'verify_otp_forgot',
        'user_id_for_resend': user_id_from_session,
    }
    return render(request, 'verify_otp.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def new_password_view(request):
    user_id = request.session.get('verified_user_id')
    if not user_id:
        return redirect('login')
    user = CustomUser.objects.get(pk=user_id)

    if request.method == 'POST':
        form = NewPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            request.session.pop('verified_user_id', None)
            messages.success(request, 'Password changed. Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = NewPasswordForm()
    return render(request, 'new_password.html', {'form': form})

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def verify_reset_otp_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please start over.')
        return redirect('forgot_password')

    if request.method == 'GET':
        resend_user_id = request.GET.get('resend')
        if resend_user_id:
            try:
                if int(resend_user_id) == user_id:
                    user = CustomUser.objects.get(pk=resend_user_id)
                    user.otp = generate_otp()
                    user.otp_created_at = timezone.now()
                    user.save()
                    send_otp_email(user.email, user.otp)
                    messages.success(request, 'New OTP sent to your email!')
                else:
                    messages.error(request, 'Invalid resend request.')
            except (CustomUser.DoesNotExist, ValueError):
                messages.error(request, 'User not found.')
            return redirect('verify_reset_otp')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        if otp and len(otp) == 6:
            try:
                user = CustomUser.objects.get(pk=user_id)
                if user.otp_created_at and timezone.now() < user.otp_created_at + timezone.timedelta(minutes=2):
                    if otp == user.otp:
                        user.otp = None
                        user.otp_created_at = None
                        user.save()
                        
                        request.session['verified_user_id'] = user.id
                        request.session.pop('reset_user_id', None)
                        
                        messages.success(request, 'OTP verified! Set your new password.')
                        return redirect('confi_new_password')
                    else:
                        messages.error(request, 'Invalid OTP.')
                else:
                    messages.error(request, 'OTP has expired.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')
        else:
            messages.error(request, 'Please enter a valid 6-digit OTP.')

    try:
        user = CustomUser.objects.get(pk=user_id)
        if user.otp_created_at:
            elapsed_time = (timezone.now() - user.otp_created_at).total_seconds()
            remaining_time = max(0, 120 - int(elapsed_time))
        else:
            remaining_time = 0
    except CustomUser.DoesNotExist:
        remaining_time = 0

    context = {
        'user_id_for_resend': user_id,
        'remaining_time': remaining_time,
    }
    return render(request, 'verify_reset_otp.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def confirm_new_password_view(request):
    logger.info("Confirm new password view accessed")
    
    verified_user_id = request.session.get('verified_user_id')
    if not verified_user_id:
        messages.error(request, 'Session expired. Please start the password reset process again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password or not confirm_password:
            messages.error(request, 'Both password fields are required.')
            return render(request, 'confi_new_password.html')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'confi_new_password.html')
        
        try:
            validate_password(new_password)
        except ValidationError as e:
            for error in e:
                messages.error(request, error)
            return render(request, 'confi_new_password.html')
        
        try:
            user = CustomUser.objects.get(pk=verified_user_id)
            user.set_password(new_password)
            user.save()
            
            request.session.pop('verified_user_id', None)
            
            messages.success(request, 'Password reset successfully! You can now login with your new password.')
            logger.info(f"Password reset successful for user ID: {verified_user_id}")
            
            return redirect('login')
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found. Please start the password reset process again.')
            return redirect('forgot_password')
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            messages.error(request, 'An error occurred while resetting your password. Please try again.')
            return render(request, 'confi_new_password.html')
    
    return render(request, 'confi_new_password.html')

@csrf_protect
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('home')
    return redirect('home')

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def send_test_email(request):
    subject = 'Test Email'
    message = 'This is a test email from your Django application.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = ['recipient_email@example.com']
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    return HttpResponse('Test email sent')

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def home_view(request):
    try:
        featured_products = Product.objects.filter(
            status__iexact='published',
            stock_quantity__gt=0
        ).select_related().prefetch_related('images')[:8]
        
        latest_products = Product.objects.filter(
            status__iexact='published',
            stock_quantity__gt=0
        ).select_related().prefetch_related('images').order_by('-created_at')[:8]
        
        context = {
            'featured_products': featured_products,
            'latest_products': latest_products,
        }
        return render(request, 'home.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading home page products: {str(e)}')
        return render(request, 'home.html', {
            'featured_products': [],
            'latest_products': []
        })
    
@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def dummy_home_view(request):
    try:
        total_products = Product.objects.count()
        published_products = Product.objects.filter(status='published').count()
        
        products = Product.objects.filter(
            status='published'
        ).select_related().prefetch_related('images')
        
        search_query = request.GET.get('search', '').strip()
        category_filter = request.GET.get('category')
        brand_filter = request.GET.get('brand')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort', 'newest')
        
        if search_query:
            products = products.filter(name__icontains=search_query)
        
        if category_filter and category_filter != 'all':
            products = products.filter(category__iexact=category_filter)
        
        if brand_filter and brand_filter != 'all':
            products = products.filter(brand__icontains=brand_filter)
        
        if min_price:
            try:
                min_price_float = float(min_price)
                products = products.filter(price__gte=min_price_float)
            except (ValueError, TypeError):
                pass
        
        if max_price:
            try:
                max_price_float = float(max_price)
                products = products.filter(price__lte=max_price_float)
            except (ValueError, TypeError):
                pass
        
        sort_options = {
            'price_low': 'price',
            'price_high': '-price',
            'name_az': 'name',
            'name_za': '-name',
            'popularity': '-created_at',
            'featured': '-created_at',
            'newest': '-created_at',
        }
        
        if sort_by in sort_options:
            products = products.order_by(sort_options[sort_by])
        else:
            products = products.order_by('-created_at')
        
        paginator = Paginator(products, 8)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        all_published = Product.objects.filter(status='published')
        available_categories = list(all_published.values_list('category', flat=True).distinct())
        available_brands = list(all_published.exclude(brand__iexact='').values_list('brand', flat=True).distinct())
        
        featured_products = products[:4]
        
        context = {
            'page_obj': page_obj,
            'products': page_obj,
            'featured_products': featured_products,
            'available_categories': available_categories,
            'available_brands': available_brands,
            'category_choices': getattr(Product, 'CATEGORY_CHOICES', []),
            'search_query': search_query,
            'current_category': category_filter,
            'current_brand': brand_filter,
            'current_sort': sort_by,
            'min_price': min_price,
            'max_price': max_price,
            'total_products': paginator.count,
        }
        
        return render(request, 'dummy.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading products: {str(e)}')
        context = {
            'page_obj': None,
            'products': [],
            'featured_products': [],
            'available_categories': [],
            'available_brands': [],
            'category_choices': [],
            'search_query': request.GET.get('search', ''),
            'current_category': request.GET.get('category'),
            'current_brand': request.GET.get('brand'),
            'current_sort': request.GET.get('sort', 'newest'),
            'min_price': request.GET.get('min_price'),
            'max_price': request.GET.get('max_price'),
            'total_products': 0,
        }
        return render(request, 'dummy.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def product_list_view(request):
    try:
        total_products = Product.objects.count()
        published_products = Product.objects.filter(status='published').count()
        
        products = Product.objects.filter(
            status='published'
        ).select_related().prefetch_related('images')
        
        search_query = request.GET.get('search', '').strip()
        category_filter = request.GET.get('category')
        brand_filter = request.GET.get('brand')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort', 'newest')
        
        if search_query:
            products = products.filter(name__icontains=search_query)
        
        if category_filter and category_filter != 'all':
            products = products.filter(category__iexact=category_filter)
        
        if brand_filter and brand_filter != 'all':
            products = products.filter(brand__icontains=brand_filter)
        
        if min_price:
            try:
                min_price_float = float(min_price)
                products = products.filter(price__gte=min_price_float)
            except (ValueError, TypeError):
                pass
        
        if max_price:
            try:
                max_price_float = float(max_price)
                products = products.filter(price__lte=max_price_float)
            except (ValueError, TypeError):
                pass
        
        sort_options = {
            'price_low': 'price',
            'price_high': '-price',
            'name_az': 'name',
            'name_za': '-name',
            'popularity': '-created_at',
            'featured': '-created_at',
            'newest': '-created_at',
        }
        
        if sort_by in sort_options:
            products = products.order_by(sort_options[sort_by])
        else:
            products = products.order_by('-created_at')
        
        paginator = Paginator(products, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        all_published = Product.objects.filter(status='published')
        available_categories = all_published.values_list('category', flat=True).distinct()
        available_brands = all_published.exclude(brand__iexact='').values_list('brand', flat=True).distinct()
        
        context = {
            'page_obj': page_obj,
            'available_categories': available_categories,
            'available_brands': available_brands,
            'category_choices': getattr(Product, 'CATEGORY_CHOICES', []),
            'search_query': search_query,
            'current_category': category_filter,
            'current_brand': brand_filter,
            'current_sort': sort_by,
            'min_price': min_price,
            'max_price': max_price,
            'total_products': paginator.count,
        }
        
        return render(request, 'product_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading products: {str(e)}')
        context = {
            'page_obj': None,
            'available_categories': [],
            'available_brands': [],
            'category_choices': [],
            'search_query': request.GET.get('search', ''),
            'current_category': request.GET.get('category'),
            'current_brand': request.GET.get('brand'),
            'current_sort': request.GET.get('sort', 'newest'),
            'min_price': request.GET.get('min_price'),
            'max_price': request.GET.get('max_price'),
            'total_products': 0,
        }
        return render(request, 'product_list.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def product_detail_view(request, pk):
    try:
        logger.info(f"Loading product detail for pk: {pk}")
        
        product = get_object_or_404(Product, pk=pk)
        
        if product.status != 'published':
            messages.error(request, 'This product is no longer available.')
            return redirect('product_list')
        
        product_images = []
        main_image = None
        
        try:
            if hasattr(product, 'images'):
                product_images = product.images.all().order_by('order')
                logger.info(f"Found {product_images.count()} images for product")
        except Exception as e:
            logger.warning(f"Error getting product images: {e}")
        
        try:
            if hasattr(product, 'get_main_image'):
                main_image = product.get_main_image()
        except Exception as e:
            logger.warning(f"Error getting main image: {e}")
        
        breadcrumbs = [
            {'name': 'Home', 'url_name': 'home'},
            {'name': 'Products', 'url_name': 'product_list'},
            {
                'name': product.get_category_display() if hasattr(product, 'get_category_display') else str(product.category), 
                'url_name': 'product_list', 
                'category': product.category
            },
            {'name': product.name, 'url_name': None}
        ]
        
        original_price = product.price
        discounted_price = original_price
        discount_amount = 0
        final_price = original_price
        
        try:
            if hasattr(product, 'get_discounted_price'):
                discounted_price = product.get_discounted_price()
                discount_amount = original_price - discounted_price if discounted_price != original_price else 0
        except Exception as e:
            logger.warning(f"Error calculating discounted price: {e}")
        
        try:
            if hasattr(product, 'get_final_price_with_tax'):
                final_price = product.get_final_price_with_tax()
            else:
                final_price = discounted_price
        except Exception as e:
            logger.warning(f"Error calculating final price: {e}")
            final_price = discounted_price
        
        stock_status = 'in_stock'
        try:
            if hasattr(product, 'stock_quantity'):
                if product.stock_quantity <= 0:
                    stock_status = 'sold_out'
                elif hasattr(product, 'is_low_stock') and product.is_low_stock():
                    stock_status = 'low_stock'
        except Exception as e:
            logger.warning(f"Error determining stock status: {e}")
        
        try:
            related_products = Product.objects.filter(
                category=product.category,
                status='published'
            ).exclude(pk=product.pk)[:4]
        except Exception as e:
            logger.warning(f"Error getting related products: {e}")
            related_products = []
        
        specs = []
        try:
            if hasattr(product, 'detailed_description') and product.detailed_description:
                specs = [
                    {'name': 'Brand', 'value': getattr(product, 'brand', 'Not specified') or 'Not specified'},
                    {'name': 'Category', 'value': product.get_category_display() if hasattr(product, 'get_category_display') else str(product.category)},
                    {'name': 'SKU', 'value': getattr(product, 'sku', 'N/A')},
                ]
        except Exception as e:
            logger.warning(f"Error building specifications: {e}")
        
        context = {
            'product': product,
            'product_images': product_images,
            'main_image': main_image,
            'breadcrumbs': breadcrumbs,
            'original_price': original_price,
            'discounted_price': discounted_price,
            'discount_amount': discount_amount,
            'final_price': final_price,
            'stock_status': stock_status,
            'related_products': related_products,
            'specs': specs,
        }
        
        logger.info(f"Successfully loaded product: {product.name}")
        return render(request, 'product_detail.html', context)
        
    except Product.DoesNotExist:
        logger.warning(f"Product not found: pk={pk}")
        messages.error(request, 'Product not found.')
        return redirect('product_list')
    except Exception as e:
        logger.error(f"Error in product_detail_view: {str(e)}", exc_info=True)
        messages.error(request, f'Error loading product: {str(e)}')
        return redirect('product_list')

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def user_profile_view(request):
    """Display user profile with all details"""
    try:
        user = CustomUser.objects.get(pk=request.user.pk)
        addresses = user.addresses.all()
        
        print(f"Profile view - User: {user.email}, Profile image: {user.profile_image}")
        
        context = {
            'user': user,
            'addresses': addresses,
        }
        return render(request, 'profile/user_profile.html', context)
        
    except Exception as e:
        print(f"Error in user_profile_view: {str(e)}")
        messages.error(request, 'Error loading profile.')
        return redirect('dummy_home')  




@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def edit_profile_view(request):
    """Edit user profile"""
    try:
        user = CustomUser.objects.get(pk=request.user.pk)
        
        if request.method == 'POST':
            form = UserProfileForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
            
                updated_user = form.save()
                
                messages.success(request, 'Profile updated successfully!')
                return redirect('user_profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = UserProfileForm(instance=user)
        
        context = {
            'form': form,
            'user': user,
        }
        return render(request, 'profile/edit_profile.html', context)
        
    except Exception as e:
        print(f"Error in edit_profile_view: {str(e)}")
        messages.error(request, 'Error loading edit profile page.')
        return redirect('user_profile')



@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def change_email_view(request):
    """Change user email with OTP verification and old email notification"""
    try:
        user = CustomUser.objects.get(pk=request.user.pk)
        
        if request.method == 'POST':
            form = EmailChangeForm(user, request.POST)
            if form.is_valid():
                new_email = form.cleaned_data['new_email']
                
               
                otp = generate_otp()
                user.new_email = new_email
                user.otp = otp
                user.otp_created_at = timezone.now()
                user.save()
                
                try:
                   
                    send_otp_email(new_email, otp)
                    
                    
                    subject = 'Email Change Request for Your Sitwell Account'
                    message = f"""
Hi {user.first_name},

We received a request to change your email to {new_email}.
If this was you, no action is needed—we've sent a verification OTP to the new address.

If this wasn't you, please secure your account immediately and contact support.

Best regards,
Sitwell Team
                    """
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [user.email], 
                        fail_silently=False,
                    )
                    
                   
                    request.session['email_change_user_id'] = user.id
                    messages.success(request, f'OTP sent to {new_email}. Please verify. A notification was also sent to your current email.')
                    return redirect('verify_email_otp')
                except Exception as e:
                    print(f"Error sending emails: {e}")
                    messages.error(request, 'Error sending emails. Please try again.')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = EmailChangeForm(user)
        
        context = {
            'form': form,
            'user': user,
        }
        return render(request, 'profile/change_email.html', context)
        
    except Exception as e:
        print(f"Error in change_email_view: {str(e)}")
        messages.error(request, 'Error loading email change page.')
        return redirect('user_profile')

@login_required
@cache_control(no_store=True)
def verify_email_otp_view(request):
    """Verify OTP for email change"""
    user_id = request.session.get('email_change_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please start over.")
        return redirect('change_email')
    
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('change_email')
    
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        if otp and len(otp) == 6:
            if user.otp_created_at and (timezone.now() - user.otp_created_at) < timezone.timedelta(minutes=2):
                if otp == user.otp:
                    # Apply the email change
                    old_email = user.email
                    user.email = user.new_email
                    user.new_email = None
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    messages.success(request, f'Email changed from {old_email} to {user.email} successfully!')
                    request.session.pop('email_change_user_id', None)
                    return redirect('user_profile')
                else:
                    messages.error(request, "Invalid OTP.")
            else:
                messages.error(request, "OTP has expired. Please try again.")
        else:
            messages.error(request, "Please enter a valid 6-digit OTP.")
    
    # Calculate remaining time for display
    remaining_time = 0
    if user.otp_created_at:
        elapsed = (timezone.now() - user.otp_created_at).total_seconds()
        remaining_time = max(0, 120 - int(elapsed))
    
    context = {
        'remaining_time': remaining_time,
    }
    return render(request, 'profile/verify_email_otp.html', context)

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def change_password_view(request):
    """Change user password"""
    try:
        user = CustomUser.objects.get(pk=request.user.pk)  
        
        if request.method == 'POST':
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                new_password = form.cleaned_data['new_password']
                user.set_password(new_password)
                user.save()
                
                # Keep user logged in after password change
                update_session_auth_hash(request, user)
                
                messages.success(request, 'Password changed successfully!')
                return redirect('user_profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = PasswordChangeForm(user)
        
        context = {
            'form': form,
            'user': user,
        }
        return render(request, 'profile/change_password.html', context)
        
    except Exception as e:
        print(f"Error in change_password_view: {str(e)}")
        messages.error(request, 'Error loading password change page.')
        return redirect('user_profile')


@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def manage_addresses_view(request):
    user = request.user
    addresses = user.addresses.all().order_by('-is_default', '-created_at')  # Assumes no is_active; add .filter(is_active=True) if using soft delete
    context = {'addresses': addresses, 'user': user}
    return render(request, 'profile/manage_addresses.html', context)





@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def add_address_view(request):
    """Add new address"""
    try:
        # Get fresh user data
        user = CustomUser.objects.get(pk=request.user.pk)
        
        if request.method == 'POST':
            form = UserAddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = user
                
                # If this is the first address, make it default
                if not user.addresses.exists():
                    address.is_default = True
                
                address.save()
                messages.success(request, 'Address added successfully!')
                return redirect('manage_addresses')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = UserAddressForm()
        
        context = {
            'form': form,
            'title': 'Add New Address',
            'user': user,
        }
        return render(request, 'profile/add_edit_address.html', context)
        
    except Exception as e:
        print(f"Error in add_address_view: {str(e)}")
        messages.error(request, 'Error adding address.')
        return redirect('manage_addresses')



@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def edit_address_view(request, address_id):
    """Edit existing address"""
    try:
        from .models import UserAddress
        address = get_object_or_404(UserAddress, id=address_id, user=request.user)
        
        if request.method == 'POST':
            form = UserAddressForm(request.POST, instance=address)
            if form.is_valid():
                form.save()
                messages.success(request, 'Address updated successfully!')
                return redirect('manage_addresses')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = UserAddressForm(instance=address)
        
        context = {
            'form': form,
            'address': address,
            'title': 'Edit Address',
            'user': request.user,
        }
        return render(request, 'profile/add_edit_address.html', context)
        
    except Exception as e:
        print(f"Error in edit_address_view: {str(e)}")
        messages.error(request, 'Error editing address.')
        return redirect('manage_addresses')

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def delete_address_view(request, address_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request. Please use the delete button.")
        return redirect('manage_addresses')
    
    try:
        with transaction.atomic():
            address = get_object_or_404(UserAddress, id=address_id, user=request.user)
            address_info = f"{address.full_name} - {address.address_type.title()}"
            
            # Reassign default if necessary
            if address.is_default:
                other_addresses = UserAddress.objects.filter(user=request.user).exclude(id=address_id).order_by('id')
                if other_addresses.exists():
                    first_other = other_addresses.first()
                    first_other.is_default = True
                    first_other.save()
            
            address.delete()  # Hard delete
            logger.info(f"Deleted address {address_id} for user {request.user.email}")
            messages.success(request, f"Address '{address_info}' deleted successfully!")
    except Exception as e:
        logger.error(f"Error deleting address {address_id}: {str(e)}")
        messages.error(request, "Error deleting address. Please try again.")
    
    return redirect('manage_addresses')




@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def set_default_address_view(request, address_id):
    """Set address as default"""
    try:
        from .models import UserAddress
        address = get_object_or_404(UserAddress, id=address_id, user=request.user)
        
        # Remove default from all user addresses
        UserAddress.objects.filter(user=request.user).update(is_default=False)
        
        address.is_default = True
        address.save()
        
        messages.success(request, 'Default address updated successfully!')
        return redirect('manage_addresses')
        
    except Exception as e:
        print(f"Error in set_default_address_view: {str(e)}")
        messages.error(request, 'Error setting default address.')
        return redirect('manage_addresses')
    

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def user_orders_view(request):
    query = request.GET.get('q', '')  # Search query
    orders = Order.objects.filter(user=request.user)
    if query:
        orders = orders.filter(Q(order_number__icontains=query) | Q(status__icontains=query))
    orders = orders.order_by('-created_at')
    
    context = {'orders': orders, 'query': query}
    return render(request, 'profile/user_orders.html', context)

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)  # Use order_number for URL
    items = order.items.all()
    history = order.status_history.all()
    
    context = {'order': order, 'items': items, 'history': history}
    return render(request, 'profile/order_detail.html', context)

@login_required
@transaction.atomic
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def cancel_order_view(request, order_id, item_id=None):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    if not order.can_be_cancelled:
        messages.error(request, "This order cannot be cancelled.")
        return redirect('order_detail', order_id=order.order_number)
    
    if request.method == 'POST':
        form = OrderCancellationForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            notes = form.cleaned_data['additional_notes']
            full_reason = dict(form.fields['reason'].choices).get(reason, '') + (f" - {notes}" if notes else "")
            
            if item_id:  # Cancel specific item
                item = get_object_or_404(OrderItem, id=item_id, order=order)
                if item.cancel_item():  # Uses the model method
                    OrderStatusHistory.objects.create(
                        order=order, 
                        old_status=item.status, 
                        new_status='cancelled', 
                        changed_by=request.user.email,
                        notes=full_reason
                    )
                    messages.success(request, f"Item cancelled successfully. Stock updated.")
                else:
                    messages.error(request, "Unable to cancel this item.")
            else:  # Cancel entire order
                if order.cancel_order(reason=full_reason, cancelled_by=request.user.email):
                    OrderStatusHistory.objects.create(
                        order=order, 
                        old_status=order.status, 
                        new_status='cancelled', 
                        changed_by=request.user.email,
                        notes=full_reason
                    )
                    messages.success(request, "Order cancelled successfully. Stock updated.")
                else:
                    messages.error(request, "Unable to cancel this order.")
            
            return redirect('order_detail', order_id=order.order_number)
    else:
        form = OrderCancellationForm()
    
    context = {'form': form, 'order': order, 'item_id': item_id}
    return render(request, 'profile/cancel_order.html', context)


'''Cart management '''
# CART MANAGEMENT VIEWS

@login_required
def add_to_cart_view(request, product_id):
    """Add product to cart or increase quantity"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        with transaction.atomic():
            # Get product and validate availability
            product = get_object_or_404(Product, id=product_id)
            
            # Check if product or category is blocked/unlisted
            if product.status != 'published':
                return JsonResponse({
                    'success': False, 
                    'message': 'This product is no longer available'
                })
            
            # Check if category is blocked (assuming you have this field)
            if hasattr(product, 'category') and hasattr(product.category, 'is_blocked'):
                if product.category.is_blocked:
                    return JsonResponse({
                        'success': False, 
                        'message': 'This product category is currently unavailable'
                    })
            
            # Check stock availability
            if product.stock_quantity <= 0:
                return JsonResponse({
                    'success': False, 
                    'message': 'This product is out of stock'
                })
            
            # Get or create user's cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Get requested quantity (default to 1)
            quantity = int(request.POST.get('quantity', 1))
            
            # Check if item already exists in cart
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 0}
            )
            
            # Calculate new quantity
            new_quantity = cart_item.quantity + quantity
            
            # Validate maximum quantity constraints
            MAX_CART_QUANTITY = 10  # Configurable limit per product
            max_allowed = min(product.stock_quantity, MAX_CART_QUANTITY)
            
            if new_quantity > max_allowed:
                return JsonResponse({
                    'success': False, 
                    'message': f'Cannot add more than {max_allowed} items of this product'
                })
            
            # Update quantity
            cart_item.quantity = new_quantity
            cart_item.save()
            
            # Remove from wishlist if it exists
            try:
                wishlist = Wishlist.objects.get(user=request.user)
                WishlistItem.objects.filter(
                    wishlist=wishlist, 
                    product=product
                ).delete()
                removed_from_wishlist = True
            except Wishlist.DoesNotExist:
                removed_from_wishlist = False
            
            # Prepare response data
            response_data = {
                'success': True,
                'message': f'Added {product.name} to cart',
                'cart_total_items': cart.total_items,
                'cart_total_amount': float(cart.total_amount),
                'item_quantity': cart_item.quantity,
                'item_subtotal': float(cart_item.subtotal),
                'removed_from_wishlist': removed_from_wishlist
            }
            
            return JsonResponse(response_data)
            
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': 'Product not found'
        })
    except ValueError:
        return JsonResponse({
            'success': False, 
            'message': 'Invalid quantity specified'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': 'An error occurred while adding to cart'
        })

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def cart_view(request):
    """Display user's shopping cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('product').prefetch_related('product__images')
        
        # Check for any out-of-stock or unavailable items
        unavailable_items = []
        available_items = []
        
        for item in cart_items:
            if not item.is_available:
                unavailable_items.append(item)
            else:
                available_items.append(item)
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'available_items': available_items,
            'unavailable_items': unavailable_items,
            'total_amount': cart.total_amount,
            'total_items': cart.total_items,
            'can_checkout': cart.is_valid_for_checkout,
        }
        
        return render(request, 'cart/cart.html', context)
        
    except Cart.DoesNotExist:
        # Create empty cart
        cart = Cart.objects.create(user=request.user)
        context = {
            'cart': cart,
            'cart_items': [],
            'available_items': [],
            'unavailable_items': [],
            'total_amount': 0,
            'total_items': 0,
            'can_checkout': False,
        }
        return render(request, 'cart/cart.html', context)
    
    except Exception as e:
        messages.error(request, 'Error loading cart')
        return redirect('dummy_home')

@login_required
def update_cart_quantity_view(request):
    """Update cart item quantity via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        cart_item_id = request.POST.get('cart_item_id')
        action = request.POST.get('action')  # 'increment' or 'decrement'
        
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        
        with transaction.atomic():
            if action == 'increment':
                new_quantity = cart_item.quantity + 1
            elif action == 'decrement':
                new_quantity = max(1, cart_item.quantity - 1)
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'})
            
            # Validate quantity constraints
            max_allowed = cart_item.max_quantity_allowed
            if new_quantity > max_allowed:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot exceed maximum quantity of {max_allowed}'
                })
            
            cart_item.quantity = new_quantity
            cart_item.save()
            
            return JsonResponse({
                'success': True,
                'new_quantity': cart_item.quantity,
                'item_subtotal': float(cart_item.subtotal),
                'cart_total': float(cart_item.cart.total_amount),
                'cart_total_items': cart_item.cart.total_items,
            })
            
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cart item not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error updating quantity'})

@login_required
def remove_from_cart_view(request, cart_item_id):
    """Remove item from cart"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('cart')
    
    try:
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        
        messages.success(request, f'Removed {product_name} from cart')
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart = Cart.objects.get(user=request.user)
            return JsonResponse({
                'success': True,
                'message': f'Removed {product_name} from cart',
                'cart_total_items': cart.total_items,
                'cart_total_amount': float(cart.total_amount),
            })
        
        return redirect('cart')
        
    except CartItem.DoesNotExist:
        messages.error(request, 'Cart item not found')
        return redirect('cart')
    except Exception as e:
        messages.error(request, 'Error removing item from cart')
        return redirect('cart')

@login_required
def clear_cart_view(request):
    """Clear all items from cart"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('cart')
    
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        messages.success(request, 'Cart cleared successfully')
        
    except Cart.DoesNotExist:
        messages.info(request, 'Cart is already empty')
    except Exception as e:
        messages.error(request, 'Error clearing cart')
    
    return redirect('cart')

@login_required
def cart_item_count_view(request):
    """Get cart item count for header display"""
    try:
        cart = Cart.objects.get(user=request.user)
        return JsonResponse({
            'success': True,
            'count': cart.total_items
        })
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': True,
            'count': 0
        })

# WISHLIST VIEWS

# @login_required
# @cache_control(no_cache=True, must_revalidate=True, no_store=True) 
# def wishlist_view(request):
#     """Display user's wishlist"""
#     try:
#         wishlist = Wishlist.objects.get(user=request.user)
#         wishlist_items = wishlist.items.select_related('product').prefetch_related('product__images')
        
#         # Check for any unavailable items (e.g., unpublished or out-of-stock)
#         unavailable_items = []
#         available_items = []
        
#         for item in wishlist_items:
#             if item.product.status != 'published' or item.product.stock_quantity <= 0:
#                 unavailable_items.append(item)
#             else:
#                 available_items.append(item)
        
#         context = {
#             'wishlist': wishlist,
#             'wishlist_items': wishlist_items,
#             'available_items': available_items,
#             'unavailable_items': unavailable_items,
#             'total_items': wishlist.items.count(),
#         }
        
#         return render(request, 'wishlist/wishlist.html', context)
        
#     except Wishlist.DoesNotExist:
#         # Create empty wishlist if none exists
#         wishlist = Wishlist.objects.create(user=request.user)
#         context = {
#             'wishlist': wishlist,
#             'wishlist_items': [],
#             'available_items': [],
#             'unavailable_items': [],
#             'total_items': 0,
#         }
#         return render(request, 'wishlist/wishlist.html', context)
    
#     except Exception as e:
#         logger.error(f"Error loading wishlist: {str(e)}")
#         messages.error(request, 'Error loading wishlist')
#         return redirect('dummy_home')




@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def checkout_view(request):
    """
    Displays the checkout page with addresses, cart items, and order summary.
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.filter(product__status='published', product__stock_quantity__gt=0)

        if not cart_items.exists():
            messages.error(request, "Your cart is empty or contains only unavailable items. Cannot proceed to checkout.")
            return redirect('cart')

        addresses = UserAddress.objects.filter(user=request.user)
        if not addresses.exists():
            messages.info(request, "Please add a shipping address before proceeding to checkout.")
            return redirect('add_address')

        # Calculate order summary (consistent with HTML: 18% tax)
        subtotal = sum(item.subtotal for item in cart_items)
        taxes = subtotal * Decimal('0.18')  # 18% tax as per HTML
        shipping = Decimal('50.00') if subtotal < 1000 else Decimal('0.00')  # Example: Free shipping over 1000
        discount = Decimal('0.00')  # Placeholder; actual discount applied in place_order

        grand_total = subtotal + taxes + shipping - discount

        context = {
            'addresses': addresses,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'taxes': taxes,
            'shipping': shipping,
            'discount': discount,
            'grand_total': grand_total,
            'user': request.user,
        }
        return render(request, 'store/checkout.html', context)
    except Cart.DoesNotExist:
        messages.error(request, "You do not have a cart.")
        return redirect('product_list')
    except Exception as e:
        logger.error(f"Error in checkout_view: {str(e)}")
        messages.error(request, "An unexpected error occurred.")
        return redirect('cart')

@login_required
@transaction.atomic
def place_order_view(request):
    """
    Handles placing the order with Cash on Delivery, applying coupon if valid.
    """
    if request.method != 'POST':
        return redirect('checkout')

    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.filter(product__status='published', product__stock_quantity__gt=0)
        
        if not cart_items.exists():
            messages.error(request, "Your cart is empty or items are out of stock.")
            return redirect('cart')
        
        address_id = request.POST.get('address')
        if not address_id:
            messages.error(request, "Please select a shipping address.")
            return redirect('checkout')
            
        shipping_address = UserAddress.objects.get(id=address_id, user=request.user)

        # Recalculate total to ensure price integrity (server-side validation)
        subtotal = sum(item.subtotal for item in cart_items)
        taxes = subtotal * Decimal('0.18')  # Consistent 18% tax
        shipping = Decimal('50.00') if subtotal < 1000 else Decimal('0.00')
        
        # Server-side coupon validation (matching client-side predefined coupons)
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        discount = Decimal('0.00')
        coupons = {
            'SAVE10': {'discount': 0.10, 'minOrder': 500},
            'FLAT50': {'discount': 50, 'minOrder': 1000},
            'FIRSTORDER': {'discount': 0.15, 'minOrder': 300}
        }
        
        if coupon_code in coupons:
            coupon = coupons[coupon_code]
            if subtotal >= coupon['minOrder']:
                if coupon['discount'] < 1:  # Percentage
                    discount = subtotal * Decimal(coupon['discount'])
                else:  # Flat
                    discount = Decimal(coupon['discount'])
        
        grand_total = subtotal + taxes + shipping - discount

        # Create the Order
        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address,
            total_amount=grand_total,
            payment_method='Cash on Delivery',
            payment_status='Pending'
        )

        # Create Order Items and update stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                product_price=item.product.price,
                quantity=item.quantity
            )
            # Decrease stock
            product = item.product
            product.stock_quantity -= item.quantity
            product.save()

        # Clear the cart
        cart.items.all().delete()
        
        messages.success(request, "Your order has been placed successfully!")
        return redirect('order_success', order_id=order.order_number)

    except UserAddress.DoesNotExist:
        messages.error(request, "Selected address not found.")
        return redirect('checkout')
    except Cart.DoesNotExist:
        messages.error(request, "Your cart was not found.")
        return redirect('product_list')
    except Exception as e:
        logger.error(f"Error in place_order_view: {str(e)}")
        messages.error(request, "An error occurred while placing your order. Please try again.")
        return redirect('checkout')

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def order_success_view(request, order_id):
    """
    Displays the order confirmation page after a successful order.
    """
    try:
        order = get_object_or_404(Order, order_number=order_id, user=request.user)
        context = {
            'order': order,
            'user': request.user,
        }
        return render(request, 'store/order_success.html', context)
    except Exception as e:
        logger.error(f"Error loading order success page: {str(e)}")
        messages.error(request, "Could not load order confirmation.")
        return redirect('user_orders')

@login_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def download_invoice_view(request, order_id):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    elements.append(Paragraph(f"Invoice for Order: {order.order_number}", styles['Title']))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Paragraph(f"Status: {order.get_status_display()}", styles['Normal']))
    elements.append(Paragraph(f"Payment Method: {order.get_payment_method_display()}", styles['Normal']))
    elements.append(Paragraph(f"Total: ${order.total_amount}", styles['Normal']))
    
    # Items Table
    data = [['Product', 'Quantity', 'Price', 'Total']]
    for item in order.items.all():
        data.append([item.product_name, item.quantity, f"${item.product_price}", f"${item.total_price}"])
    table = Table(data)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), 'grey'), ('TEXTCOLOR', (0, 0), (-1, 0), 'white')]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=invoice_{order.order_number}.pdf'
    return response

@login_required
@transaction.atomic
@cache_control(no_cache=True, must_revalidate=True, no_store=True) 
def return_order_view(request, order_id):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    if not order.can_be_returned:
        messages.error(request, "This order cannot be returned.")
        return redirect('order_detail', order_id=order.order_number)
    
    if request.method == 'POST':
        form = OrderReturnForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            if order.return_order(reason=reason, returned_by=request.user.email):
                OrderStatusHistory.objects.create(
                    order=order, 
                    old_status='delivered', 
                    new_status='refunded', 
                    changed_by=request.user.email,
                    notes=reason
                )
                messages.success(request, "Order returned successfully. Stock updated.")
                return redirect('order_detail', order_id=order.order_number)
            else:
                messages.error(request, "Unable to return this order.")
    else:
        form = OrderReturnForm()
    
    context = {'form': form, 'order': order}
    return render(request, 'profile/return_order.html', context)




def contact(request):
    """Display contact page"""
    return render(request, 'contact.html')

@require_http_methods(["POST"])
def contact_submit(request):
    """Handle contact form submission"""
    try:
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject', 'No Subject')
        message = request.POST.get('message')
        
        # Validate required fields
        if not all([name, email, message]):
            return JsonResponse({
                'success': False, 
                'message': 'Please fill in all required fields'
            })
        
        # Compose email
        email_subject = f'Sitwell Contact Form: {subject}'
        email_body = f"""
        New contact form submission from Sitwell website:
        
        Name: {name}
        Email: {email}
        Subject: {subject}
        
        Message:
        {message}
        
        ---
        Sent from Sitwell Contact Form
        """
        
        # Send email
        send_mail(
            email_subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Thank you! Your message has been sent successfully.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'An error occurred: {str(e)}'
        })
    


def about(request):
    """Display about page"""
    return render(request, 'about.html')
