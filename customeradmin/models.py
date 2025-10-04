from django.db import models
from PIL import Image as PILImage
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager that includes all objects, even soft-deleted ones"""
    def get_queryset(self):
        return super().get_queryset()


class CustomerVisibleManager(SoftDeleteManager):
    """Manager for customer-visible products only"""
    def get_queryset(self):
        return super().get_queryset().filter(
            is_blocked=False,
            status='published'
        )


class Product(models.Model):
    
    STATUS_CHOICES = [
        ('published', 'Published'),
        ('draft', 'Draft'),
        ('out-of-stock', 'Out of Stock'),
        ('low-stock', 'Low Stock'),
        ('blocked', 'Blocked'),  
    ]
    
    CATEGORY_CHOICES = [
        ('sofa', 'Sofa'),
        ('chair', 'Chair'),
        ('table', 'Table'),
        ('bed', 'Bed'), 
        ('storage', 'Storage'),
        ('accessories', 'Accessories'),
    ]
    
    DISCOUNT_TYPES = [
        ('none', 'No Discount'),
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    TAX_TYPES = [
        ('free', 'Tax Free'),
        ('taxable', 'Taxable'),
    ]
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='sofa')
    brand = models.CharField(max_length=100, blank=True)
    short_description = models.TextField(blank=True)
    detailed_description = models.TextField(blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='none')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Enter percentage (e.g., 10 for 10%) or fixed amount")
    
    tax_type = models.CharField(max_length=20, choices=TAX_TYPES, default='free')
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="VAT percentage (e.g., 18 for 18%)")
    
    stock_quantity = models.IntegerField()
    low_stock_threshold = models.IntegerField(default=5, help_text="Alert when stock falls below this number")
    manage_stock = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=100, null=True, blank=True)
    

    is_blocked = models.BooleanField(default=False, help_text="Block the product from customer view")
    blocked_at = models.DateTimeField(null=True, blank=True, help_text="When was product blocked")
    blocked_by = models.CharField(max_length=100, blank=True, null=True, help_text="Who blocked the product")
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
  
    objects = SoftDeleteManager() 
    all_objects = AllObjectsManager()  
    customer_visible = CustomerVisibleManager() 
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['created_at']),
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['is_blocked']),  
            models.Index(fields=['is_blocked', 'status']),  
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def soft_delete(self, deleted_by=None):
        """Soft delete the product"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by or 'Unknown'
        self.save()
    
    def restore(self):
        """Restore a soft-deleted product"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    def hard_delete(self):
        """Permanently delete the product"""
        super().delete()
    
    def block_product(self, blocked_by=None):
        """Block the product from customer view"""
        from django.utils import timezone
        self.is_blocked = True
        self.blocked_at = timezone.now()
        self.blocked_by = blocked_by or 'Admin'
        
        self.status = 'blocked'
        self.save(update_fields=['is_blocked', 'blocked_at', 'blocked_by', 'status'])
    
    def unblock_product(self):
        """Unblock the product and restore appropriate status"""
        self.is_blocked = False
        self.blocked_at = None
        self.blocked_by = None
        
        if self.status == 'blocked':
            if self.stock_quantity <= 0:
                self.status = 'out-of-stock'
            elif self.is_low_stock():
                self.status = 'low-stock'
            else:
                self.status = 'published'
        
        self.save(update_fields=['is_blocked', 'blocked_at', 'blocked_by', 'status'])
    
    def is_visible_to_customers(self):
        """Check if product should be visible to customers"""
        return (
            not self.is_deleted and 
            not self.is_blocked and 
            self.status in ['published', 'out-of-stock', 'low-stock']
        )
    
    def is_available_for_purchase(self):
        """Check if product is available for customer purchase"""
        return (
            not self.is_deleted and 
            not self.is_blocked and 
            self.status == 'published' and 
            self.stock_quantity > 0
        )
    
    def get_status_display_admin(self):
        """Get status display for admin with blocking indicator"""
        status_display = self.get_status_display()
        if self.is_blocked:
            return f"🚫 {status_display}"
        return status_display
    
    def get_main_image(self):
        """Get the primary image or first available image"""
        primary_images = self.images.filter(is_primary=True)
        if primary_images.exists():
            return primary_images.first()
        elif self.images.exists():
            return self.images.first()
        return None
    
    def get_main_image_url(self):
        """Get the URL of the main image"""
        main_image = self.get_main_image()
        if main_image and main_image.image:
            return main_image.image.url
        return None
    
    def get_discounted_price(self):
        """Calculate the price after discount"""
        if self.discount_type == 'percentage' and self.discount_value > 0:
            discount_amount = self.price * (self.discount_value / 100)
            return self.price - discount_amount
        elif self.discount_type == 'fixed' and self.discount_value > 0:
            return max(0, self.price - self.discount_value)
        return self.price
    
    def get_final_price_with_tax(self):
        """Calculate final price including tax"""
        discounted_price = self.get_discounted_price()
        if self.tax_type == 'taxable' and self.vat_percentage > 0:
            tax_amount = discounted_price * (self.vat_percentage / 100)
            return discounted_price + tax_amount
        return discounted_price
    
    def get_discount_amount(self):
        """Get the discount amount"""
        return self.price - self.get_discounted_price()
    
    def is_low_stock(self):
        """Check if product is low on stock"""
        return self.stock_quantity <= self.low_stock_threshold
    
    # NEW: Override save method for auto status updates
    def save(self, *args, **kwargs):
        """Override save to auto-update status based on stock quantity and other conditions"""
        
        # First, handle stock-based status changes
        if hasattr(self, 'stock_quantity') and self.stock_quantity is not None:
            # Don't change status if product is blocked or soft-deleted
            if not self.is_blocked and not self.is_deleted:
                if self.stock_quantity == 0:
                    
                    self.status = 'out-of-stock'
                elif self.stock_quantity <= self.low_stock_threshold:
                    
                    if self.status == 'out-of-stock':  
                        self.status = 'low-stock'
                elif self.status in ['out-of-stock', 'low-stock'] and self.stock_quantity > self.low_stock_threshold:
                    self.status = 'published'
        
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def save(self, *args, **kwargs):
        """Resize image before saving"""
        if self.image:
            self.image = self.resize_image(self.image, 800, 600)
        super().save(*args, **kwargs)
    
    def resize_image(self, image_file, max_width, max_height):
        """Resize image to specified dimensions"""
        img = PILImage.open(image_file)
        
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return InMemoryUploadedFile(
            output, 'ImageField',
            f"{image_file.name.split('.')[0]}.jpg",
            'image/jpeg',
            sys.getsizeof(output), None
        )
    
    def __str__(self):
        return f"{self.product.name} - Image {self.order + 1}"


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_listed = models.BooleanField(default=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = SoftDeleteManager()  
    all_objects = AllObjectsManager()  
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_deleted']),
        ]
        ordering = ['-created_at'] 
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name
    
    def soft_delete(self, deleted_by=None):
        """Soft delete the category"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by or 'Unknown'
        self.save()
    
    def restore(self):
        """Restore a soft-deleted category"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()



