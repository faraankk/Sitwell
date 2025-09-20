from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import SignUpForm, OTPForm, NewPasswordForm, LoginForm, ForgotPasswordForm
from .models import CustomUser
from .utils import generate_otp, send_otp_email
import random
import string
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from customeradmin.models import Product, Category, ProductImage
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)

@never_cache
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

@never_cache
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
@never_cache
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

@never_cache
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

@never_cache
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

@never_cache
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

@never_cache
def home_view(request):
    featured_products = Product.objects.filter(
        status='published',
        stock_quantity__gt=0
    )[:8]
    
    latest_products = Product.objects.filter(
        status='published',
        stock_quantity__gt=0
    ).order_by('-created_at')[:8]
    
    context = {
        'featured_products': featured_products,
        'latest_products': latest_products,
    }
    return render(request, 'home.html', context)

# def generate_otp():
#     otp = ''.join(random.choices(string.digits, k=6))
#     print(f"Generated OTP: {otp}")
#     return otp

@never_cache
def send_test_email(request):
    subject = 'Test Email'
    message = 'This is a test email from your Django application.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = ['recipient_email@example.com']
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    return HttpResponse('Test email sent')

@csrf_protect
@never_cache
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('home')
    return redirect('home')

@login_required
@never_cache
def dummy_home_view(request):
    products = Product.objects.filter(
        status='published'
    ).select_related().prefetch_related('images')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(short_description__icontains=search_query) |
            Q(detailed_description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        products = products.filter(category=category_filter)
    
    brand_filter = request.GET.get('brand')
    if brand_filter and brand_filter != 'all':
        products = products.filter(brand__icontains=brand_filter)
    
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass
    
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name_az':
        products = products.order_by('name')
    elif sort_by == 'name_za':
        products = products.order_by('-name')
    elif sort_by == 'popularity':
        products = products.order_by('-created_at')
    elif sort_by == 'featured':
        products = products.order_by('-created_at')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('-created_at')
    
    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    available_categories = Product.objects.filter(
        status='published'
    ).values_list('category', flat=True).distinct()
    
    available_brands = Product.objects.filter(
        status='published'
    ).exclude(brand='').values_list('brand', flat=True).distinct()
    
    featured_products = products[:4]
    
    context = {
        'page_obj': page_obj,
        'products': page_obj,
        'featured_products': featured_products,
        'available_categories': available_categories,
        'available_brands': available_brands,
        'category_choices': Product.CATEGORY_CHOICES,
        'search_query': search_query,
        'current_category': category_filter,
        'current_brand': brand_filter,
        'current_sort': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'total_products': products.count(),
    }
    return render(request, 'dummy.html', context)

@never_cache
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

@never_cache
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

@never_cache
def product_list_view(request):
    products = Product.objects.filter(
        status='published'
    ).select_related().prefetch_related('images')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(short_description__icontains=search_query) |
            Q(detailed_description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        products = products.filter(category=category_filter)
    
    brand_filter = request.GET.get('brand')
    if brand_filter and brand_filter != 'all':
        products = products.filter(brand__icontains=brand_filter)
    
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass
    
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name_az':
        products = products.order_by('name')
    elif sort_by == 'name_za':
        products = products.order_by('-name')
    elif sort_by == 'popularity':
        products = products.order_by('-created_at')
    elif sort_by == 'featured':
        products = products.order_by('-created_at')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('-created_at')
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    available_categories = Product.objects.filter(
        status='published'
    ).values_list('category', flat=True).distinct()
    
    available_brands = Product.objects.filter(
        status='published'
    ).exclude(brand='').values_list('brand', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'available_categories': available_categories,
        'available_brands': available_brands,
        'category_choices': Product.CATEGORY_CHOICES,
        'search_query': search_query,
        'current_category': category_filter,
        'current_brand': brand_filter,
        'current_sort': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'total_products': products.count(),
    }
    return render(request, 'product_list.html', context)

@never_cache
def product_detail_view(request, pk):
    try:
        product = get_object_or_404(Product, pk=pk)
        
        if product.status != 'published':
            messages.error(request, 'This product is no longer available.')
            return redirect('product_list')
        
        product_images = product.images.all().order_by('order')
        main_image = product.get_main_image()
        
        breadcrumbs = [
            {'name': 'Home', 'url_name': 'home'},
            {'name': 'Products', 'url_name': 'product_list'},
            {'name': product.get_category_display(), 'url_name': 'product_list', 'category': product.category},
            {'name': product.name, 'url_name': None}
        ]
        
        original_price = product.price
        discounted_price = product.get_discounted_price()
        discount_amount = original_price - discounted_price if discounted_price != original_price else 0
        final_price = product.get_final_price_with_tax()
        
        stock_status = 'in_stock'
        if product.stock_quantity <= 0:
            stock_status = 'sold_out'
        elif product.is_low_stock():
            stock_status = 'low_stock'
        
        related_products = Product.objects.filter(
            category=product.category,
            status='published'
        ).exclude(pk=product.pk)[:4]
        
        specs = []
        if product.detailed_description:
            specs = [
                {'name': 'Brand', 'value': product.brand or 'Not specified'},
                {'name': 'Category', 'value': product.get_category_display()},
                {'name': 'SKU', 'value': product.sku},
            ]
        
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
        return render(request, 'product_detail.html', context)
        
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('product_list')