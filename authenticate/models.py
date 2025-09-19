from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

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
    
    # ADD THESE NEW BLOCK/UNBLOCK FIELDS
    is_blocked = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.CharField(max_length=100, null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    # ADD THESE NEW METHODS
    def block_user(self, blocked_by=None):
        """Block the user"""
        from django.utils import timezone
        self.is_blocked = True
        self.blocked_at = timezone.now()
        self.blocked_by = blocked_by or 'Admin'
        self.save()
    
    def unblock_user(self):
        """Unblock the user"""
        self.is_blocked = False
        self.blocked_at = None
        self.blocked_by = None
        self.save()

# In customeradmin/models.py - Product class
def get_main_image(self):
    """Get the main product image"""
    main_img = self.images.filter(is_main=True).first()
    return main_img if main_img else self.images.first()

def get_main_image_url(self):
    """Get main image URL or None"""
    main_img = self.get_main_image()
    return main_img.image.url if main_img else None

def get_discounted_price(self):
    """Calculate price after discount"""
    if self.discount_type == 'percentage' and self.discount_value > 0:
        return self.price * (1 - self.discount_value / 100)
    elif self.discount_type == 'fixed' and self.discount_value > 0:
        return max(0, self.price - self.discount_value)
    return self.price

def get_final_price_with_tax(self):
    """Calculate final price including tax"""
    discounted = self.get_discounted_price()
    if self.tax_type == 'taxable' and hasattr(self, 'tax_rate'):
        return discounted * (1 + self.tax_rate / 100)
    return discounted

def is_low_stock(self):
    """Check if stock is low (less than 10)"""
    return 0 < self.stock_quantity < 10
