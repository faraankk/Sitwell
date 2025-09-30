from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import re
from django.utils import timezone
from customeradmin.models import Product
import random
import string 

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    
    is_blocked = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.CharField(max_length=100, null=True, blank=True)
    
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    new_email = models.EmailField(blank=True, null=True)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_token_created_at = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def block_user(self, blocked_by=None):
        from django.utils import timezone
        self.is_blocked = True
        self.blocked_at = timezone.now()
        self.blocked_by = blocked_by or 'Admin'
        self.save()
    
    def unblock_user(self):
        self.is_blocked = False
        self.blocked_at = None
        self.blocked_by = None
        self.save()

    def clean_phone_number(self):
        """Remove all non-digit characters from phone number"""
        if self.phone_number:
            from .utils import clean_phone_number
            self.phone_number = clean_phone_number(self.phone_number)
    
    def save(self, *args, **kwargs):
        # Clean phone number before saving
        self.clean_phone_number()
        super().save(*args, **kwargs)


class UserAddress(models.Model):
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.address_type} ({self.city})"
    
    def clean_phone_number(self):
        if self.phone_number:
            # Fixed regex - removed double backslash
            self.phone_number = re.sub(r'[^\d]', '', self.phone_number)

    def save(self, *args, **kwargs):
        # Clean phone number before saving
        self.clean_phone_number()
        super().save(*args, **kwargs)


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
    ]
    
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='cod')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.ForeignKey('UserAddress', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Order tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Cancellation
    can_cancel = models.BooleanField(default=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.CharField(max_length=50, blank=True, null=True)
    
    # Shipping details
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_carrier = models.CharField(max_length=100, blank=True, null=True)
    
    # Return fields
    return_reason = models.TextField(blank=True, null=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = 'ORD' + ''.join(random.choices(string.digits, k=8))
        super().save(*args, **kwargs)
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        cancellable_statuses = ['pending', 'confirmed']
        return self.status in cancellable_statuses and self.can_cancel
    
    @property
    def can_be_returned(self):
        """Check if order can be returned (only if delivered)"""
        return self.status == 'delivered'
    
    def cancel_order(self, reason=None, cancelled_by='user'):
        """Cancel the order"""
        if self.can_be_cancelled:
            self.status = 'cancelled'
            self.can_cancel = False
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.cancelled_by = cancelled_by
            self.save()
            
            # Increment stock for all items
            for item in self.items.all():
                if item.product:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            return True
        return False
    
    def return_order(self, reason, returned_by='user'):
        """Return the order (only if delivered)"""
        if self.can_be_returned:
            self.status = 'refunded'
            self.return_reason = reason
            self.returned_at = timezone.now()
            self.returned_by = returned_by
            self.save()
            
            # Increment stock for all items on return
            for item in self.items.all():
                if item.product:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            return True
        return False

class OrderItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Optional: Link to actual product
    product = models.ForeignKey('customeradmin.Product', on_delete=models.SET_NULL, null=True, blank=True)
    
    # For partial cancellation/return
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')
    is_cancelled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.product_price * self.quantity
        super().save(*args, **kwargs)
    
    def cancel_item(self):
        """Cancel a specific item in the order"""
        if not self.is_cancelled and self.order.can_be_cancelled:
            self.is_cancelled = True
            self.status = 'cancelled'
            self.save()
            
            # Increment stock for this item
            self.increment_stock()
            return True
        return False
    
    def increment_stock(self):
        """Increment product stock by this item's quantity"""
        if self.product:
            self.product.stock_quantity += self.quantity
            self.product.save()

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} -> {self.new_status}"


class Cart(models.Model):
    """User's shopping cart"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        """Get total number of items in cart"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_amount(self):
        """Calculate total cart amount"""
        total = 0
        for item in self.items.all():
            total += item.subtotal
        return total
    
    @property
    def is_valid_for_checkout(self):
        """Check if cart can proceed to checkout"""
        return all(item.is_available for item in self.items.all())


class CartItem(models.Model):
    """Individual items in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('customeradmin.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('cart', 'product')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.cart.user.email}'s cart"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this cart item"""
        return self.quantity * self.product.price
    
    @property
    def is_available(self):
        """Check if product is available for purchase"""
        return (
            self.product.status == 'published' and
            self.product.stock_quantity >= self.quantity and
            not getattr(self.product.category, 'is_blocked', False)
        )
    
    @property
    def max_quantity_allowed(self):
        """Maximum quantity that can be ordered"""
        MAX_CART_QUANTITY = 10  # You can make this configurable
        return min(self.product.stock_quantity, MAX_CART_QUANTITY)
    
    def clean(self):
        """Validate cart item before saving"""
        if self.quantity > self.max_quantity_allowed:
            raise models.ValidationError(
                f"Quantity cannot exceed {self.max_quantity_allowed} for {self.product.name}"
            )


class Wishlist(models.Model):
    """User's wishlist"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wishlist for {self.user.email}"


class WishlistItem(models.Model):
    """Individual items in wishlist"""
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('customeradmin.Product', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('wishlist', 'product')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.email}'s wishlist"




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from .models import Order, OrderItem, OrderStatusHistory
from .forms import OrderCancellationForm, OrderReturnForm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from django.views.decorators.cache import cache_control

@login_required
@cache_control(no_store=True)
def user_orders_view(request):
    query = request.GET.get('q', '')  # Search query
    orders = Order.objects.filter(user=request.user)
    if query:
        orders = orders.filter(Q(order_number__icontains=query) | Q(status__icontains=query))
    orders = orders.order_by('-created_at')
    
    context = {'orders': orders, 'query': query}
    return render(request, 'profile/user_orders.html', context)

@login_required
@cache_control(no_store=True)
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)  # Use order_number for URL
    items = order.items.all()
    history = order.status_history.all()
    
    context = {'order': order, 'items': items, 'history': history}
    return render(request, 'profile/order_detail.html', context)

@login_required
@transaction.atomic
@cache_control(no_store=True)
def cancel_order_view(request, order_id, item_id=None):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    if not order.can_be_cancelled():
        messages.error(request, "This order cannot be cancelled.")
        return redirect('order_detail', order_id=order.order_number)
    
    if request.method == 'POST':
        form = OrderCancellationForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            notes = form.cleaned_data['additional_notes']
            full_reason = reason + (f" - {notes}" if notes else "")
            
            if item_id:  # Cancel specific item
                item = get_object_or_404(OrderItem, id=item_id, order=order)
                item.status = 'cancelled'
                item.save()
                item.increment_stock()
                OrderStatusHistory.objects.create(order=order, old_status=item.status, new_status='cancelled', notes=full_reason)
                messages.success(request, f"Item cancelled successfully. Stock updated.")
            else:  # Cancel entire order
                order.status = 'cancelled'
                order.cancellation_reason = full_reason
                order.save()
                for item in order.items.all():
                    item.status = 'cancelled'
                    item.save()
                    item.increment_stock()
                OrderStatusHistory.objects.create(order=order, old_status=order.status, new_status='cancelled', notes=full_reason)
                messages.success(request, "Order cancelled successfully. Stock updated.")
            
            return redirect('order_detail', order_id=order.order_number)
    else:
        form = OrderCancellationForm()
    
    context = {'form': form, 'order': order, 'item_id': item_id}
    return render(request, 'profile/cancel_order.html', context)

@login_required
@transaction.atomic
@cache_control(no_store=True)
def return_order_view(request, order_id):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    if not order.can_be_returned():
        messages.error(request, "This order cannot be returned.")
        return redirect('order_detail', order_id=order.order_number)
    
    if request.method == 'POST':
        form = OrderReturnForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            order.status = 'returned'
            order.return_reason = reason
            order.save()
            for item in order.items.all():
                item.status = 'returned'
                item.save()
                item.increment_stock()  # Increment stock on return
            OrderStatusHistory.objects.create(order=order, old_status='delivered', new_status='returned', notes=reason)
            messages.success(request, "Order returned successfully. Stock updated.")
            return redirect('order_detail', order_id=order.order_number)
    else:
        form = OrderReturnForm()
    
    context = {'form': form, 'order': order}
    return render(request, 'profile/return_order.html', context)

@login_required
@cache_control(no_store=True)
def download_invoice_view(request, order_id):
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Invoice for Order: {order.order_number}")
    p.drawString(100, 730, f"Date: {order.created_at.strftime('%Y-%m-%d')}")
    p.drawString(100, 710, f"Status: {order.status}")
    p.drawString(100, 690, f"Total: ${order.total_amount}")
    
    y = 660
    for item in order.items.all():
        p.drawString(100, y, f"{item.product.name} x {item.quantity} - ${item.price}")
        y -= 20
    
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=invoice_{order.order_number}.pdf'
    return response
