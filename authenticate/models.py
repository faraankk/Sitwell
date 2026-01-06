from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import re
from django.utils import timezone
from customeradmin.models import Product
import random
import string 
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


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
        if self.phone_number:
            self.phone_number = re.sub(r'[^\d]', '', self.phone_number)
    
    # def save(self, *args, **kwargs):
    #     self.clean_phone_number()
    #     super().save(*args, **kwargs)
    
    
    def save(self, *args, **kwargs):
        self.clean_phone_number()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Referral.objects.get_or_create(referrer=self, defaults={'code': generate_ref_code()})

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
            self.phone_number = re.sub(r'[^\d]', '', self.phone_number)

    def save(self, *args, **kwargs):
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
        ('refund_pending', 'Refund Pending'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('wallet', 'Wallet'),
    ]
    
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='cod')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    shipping_address = models.ForeignKey('UserAddress', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    can_cancel = models.BooleanField(default=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.CharField(max_length=50, blank=True, null=True)
    
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_carrier = models.CharField(max_length=100, blank=True, null=True)
    
    return_reason = models.TextField(blank=True, null=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.CharField(max_length=50, blank=True, null=True)

    razorpay_order_id   = models.CharField(max_length=90, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=90, blank=True, null=True)
    
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    wallet_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refund_processed_at = models.DateTimeField(null=True, blank=True)
    refund_processed_by = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = 'ORD' + ''.join(random.choices(string.digits, k=8))
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        self.subtotal = Decimal('0.00')
        original_total = Decimal('0.00')
        for item in self.items.all():
            self.subtotal += item.total_price
            if item.product:
                original_price = item.product.price
                original_total += original_price * item.quantity
        self.discount_amount = original_total - self.subtotal
        self.tax_amount = self.subtotal * Decimal('0.18')
        self.shipping_charge = Decimal('0.00') if self.subtotal >= Decimal('500.00') else Decimal('50.00')
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_charge
        self.save(update_fields=['subtotal', 'discount_amount', 'tax_amount', 'shipping_charge', 'total_amount'])
        return {
            'subtotal': self.subtotal,
            'discount_amount': self.discount_amount,
            'tax_amount': self.tax_amount,
            'shipping_charge': self.shipping_charge,
            'total_amount': self.total_amount
        }
    
    @property
    def can_be_cancelled(self):
        cancellable_statuses = ['pending', 'confirmed']
        return self.status in cancellable_statuses and self.can_cancel
    
    @property
    def can_be_returned(self):
        return self.status == 'delivered'
    
    def process_wallet_refund(self, amount=None, processed_by="System"):
        """Refund order amount to user's wallet."""
        if amount is None:
            amount = self.total_amount
        try:
            wallet, created = Wallet.objects.get_or_create(user=self.user)
            wallet.credit(amount, self, f"Refund for order {self.order_number}")
            self.refund_processed_at = timezone.now()
            self.refund_processed_by = processed_by
            self.save(update_fields=['refund_processed_at', 'refund_processed_by'])
            return True
        except Exception as e:
            logger.error(f"Wallet refund error for order {self.order_number}: {e}")
            return False
    
    def cancel_order(self, reason=None, cancelled_by='user'):
        """Cancel order + instant wallet refund for paid orders."""
        if self.can_be_cancelled:
            self.status = 'cancelled'
            self.can_cancel = False
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.cancelled_by = cancelled_by
            self.save()
            
            for item in self.items.all():
                if item.product:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
           
            if self.payment_status == 'paid':
                self.process_wallet_refund(processed_by=cancelled_by)
            return True
        return False
    
    def return_order(self, reason, returned_by='user'):
        """Return order -> status = refund_pending (admin must confirm)."""
        if self.can_be_returned:
            self.status = 'refund_pending'
            self.return_reason = reason
            self.returned_at = timezone.now()
            self.returned_by = returned_by
            self.refund_requested_at = timezone.now()
            self.save()
            
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
    product = models.ForeignKey('customeradmin.Product', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.product_price * self.quantity
        super().save(*args, **kwargs)
    
    def cancel_item(self):
        if not self.is_cancelled and self.order.can_be_cancelled:
            self.is_cancelled = True
            self.status = 'cancelled'
            self.save()
            if self.product:
                self.product.stock_quantity += self.quantity
                self.product.save()
            return True
        return False


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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_amount(self):
        total = 0
        for item in self.items.all():
            total += item.subtotal
        return total
    
    @property
    def is_valid_for_checkout(self):
        return all(item.is_available for item in self.items.all())


class CartItem(models.Model):
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
        return self.quantity * self.product.get_discounted_price()
    
    @property
    def is_available(self):
        return (
            self.product.status == 'published' and
            self.product.stock_quantity >= self.quantity and
            not getattr(self.product.category, 'is_blocked', False)
        )
    
    @property
    def max_quantity_allowed(self):
        MAX_CART_QUANTITY = 10
        return min(self.product.stock_quantity, MAX_CART_QUANTITY)


class Wishlist(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wishlist for {self.user.email}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('customeradmin.Product', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('wishlist', 'product')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.email}'s wishlist"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_percent = models.PositiveIntegerField(default=10)  # 1-100
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    max_usage = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    # audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "CustomUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="coupons_created"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} – {self.discount_percent}% off"

    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_to
            and self.used_count < self.max_usage
        )

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        """
        Return discount amount (never more than order_amount).
        """
        try:
            if not self.is_valid:
                return Decimal("0.00")
            if order_amount < self.min_order_amount:
                return Decimal("0.00")

            if isinstance(order_amount, (int, float)):
                order_amount = Decimal(str(order_amount))

            discount = order_amount * (Decimal(self.discount_percent) / Decimal("100"))
            return min(discount, order_amount)
        except Exception as exc:
            logger.exception("Coupon discount error")
            return Decimal("0.00")

    #  model validation 
    def clean(self):
        super().clean()
        if self.valid_to <= self.valid_from:
            raise ValidationError("Valid-to must be after valid-from.")
        if not (1 <= self.discount_percent <= 100):
            raise ValidationError("Discount % must be between 1 and 100.")
        if self.max_usage <= 0:
            raise ValidationError("Max usage must be positive.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['coupon', 'user']  


#  WALLET 
class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)   # ← NEW
    updated_at = models.DateTimeField(auto_now=True)       # ← NEW (optional but useful)

    def __str__(self):
        return f"{self.user.email} – ₹{self.balance}"

    def credit(self, amount, order=None, note=''):
        from decimal import Decimal
        amount = Decimal(str(amount))
        self.balance += amount
        self.save(update_fields=['balance'])
        WalletTransaction.objects.create(
            wallet=self,
            order=order,
            amount=amount,
            txn_type='credit',
            note=note or f"Refund for {order.order_number}" if order else "Wallet credited"
        )

    def debit(self, amount, order=None, note=''):
        from decimal import Decimal
        amount = Decimal(str(amount))
        if amount > self.balance:
            raise ValueError("Insufficient wallet balance")
        self.balance -= amount
        self.save(update_fields=['balance'])
        WalletTransaction.objects.create(
            wallet=self,
            order=order,
            amount=amount,
            txn_type='debit',
            note=note or f"Used for {order.order_number}" if order else "Wallet debited"
        )

    
    def can_pay(self, amount):
        from decimal import Decimal
        amount = Decimal(str(amount))
        return self.balance >= amount


class WalletTransaction(models.Model):
    TXN_TYPES = [('credit', 'Credit'), ('debit', 'Debit')]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    txn_type = models.CharField(max_length=10, choices=TXN_TYPES, default='credit')
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.txn_type.title()} ₹{self.amount} – {self.wallet.user.email}"
    

