from django.forms import inlineformset_factory
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import Product, ProductImage, Category


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200',
        'placeholder': 'Enter your username',
        'autofocus': True
    }))
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200',
        'placeholder': 'Enter your password'
    }))


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'category', 'brand', 'price', 'discount_type', 'discount_value',
            'tax_type', 'vat_percentage', 'stock_quantity', 'low_stock_threshold', 'manage_stock',
            'status', 'short_description', 'detailed_description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Product name...'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Product SKU...'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'brand': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Product brand...'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Base price...',
                'step': '0.01'
            }),
            'discount_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': '0',
                'step': '0.01'
            }),
            'tax_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'vat_percentage': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': '0',
                'step': '0.01'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Stock quantity...'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': '5'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Brief product description...'
            }),
            'detailed_description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 6,
                'placeholder': 'Detailed product description...'
            }),
            'manage_stock': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make these fields not required
        self.fields['discount_type'].required = False
        self.fields['discount_value'].required = False
        self.fields['tax_type'].required = False
        self.fields['vat_percentage'].required = False
        self.fields['low_stock_threshold'].required = False
        self.fields['manage_stock'].required = False
        self.fields['brand'].required = False
        self.fields['short_description'].required = False
        self.fields['detailed_description'].required = False

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if sku:
            # Check for duplicate SKU (excluding current instance if editing)
            existing = Product.objects.filter(sku=sku)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("Product with this SKU already exists.")
        return sku

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price

    def clean_stock_quantity(self):
        stock = self.cleaned_data.get('stock_quantity')
        if stock and stock < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock

    def clean_discount_value(self):
        discount_type = self.cleaned_data.get('discount_type')
        discount_value = self.cleaned_data.get('discount_value')
        
        if discount_type and discount_type != 'none' and discount_value:
            if discount_type == 'percentage' and (discount_value < 0 or discount_value > 100):
                raise forms.ValidationError("Percentage discount must be between 0 and 100.")
            elif discount_type == 'fixed' and discount_value < 0:
                raise forms.ValidationError("Fixed discount cannot be negative.")
        
        return discount_value


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary', 'order']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-20 px-2 py-1 border border-gray-300 rounded text-sm',
                'min': '0'
            })
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Only validate if this is a newly uploaded file (not an existing ImageFieldFile)
            if hasattr(image, 'content_type') and hasattr(image, 'size'):
                # Check file size (5MB limit)
                if image.size > 5 * 1024 * 1024:
                    raise forms.ValidationError("Image file too large. Maximum size is 5MB.")
                
                # Check file type
                if not image.content_type.startswith('image/'):
                    raise forms.ValidationError("File must be an image.")
                
                # Check file extension
                valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                if not any(image.name.lower().endswith(ext) for ext in valid_extensions):
                    raise forms.ValidationError("Invalid image format. Use JPG, PNG, GIF, or WebP.")
        
        return image


# Enhanced formset for multiple images with proper validation
ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage,
    form=ProductImageForm,
    fields=['image', 'is_primary', 'order'],
    extra=0,  # We handle this dynamically with JavaScript
    min_num=3,  # Minimum 3 images required
    validate_min=True,  # Enforce minimum validation
    max_num=6,  # Maximum 6 images allowed
    validate_max=True,  # Enforce maximum validation
    can_delete=True,  # Allow deletion of existing images
    can_order=True,  # Allow reordering of images
)


# Legacy formset (keep for backward compatibility if needed)
ProductImageFormSetLegacy = inlineformset_factory(
    Product, 
    ProductImage,
    form=ProductImageForm,
    fields=['image', 'is_primary', 'order'],
    extra=4,  # Show 4 empty forms
    max_num=6,  # Maximum 6 images
    can_delete=True
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'thumbnail', 'is_listed']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Type category name here...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none',
                'rows': 4,
                'placeholder': 'Type category description here...'
            }),
            'thumbnail': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*'
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            existing = Category.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("Category with this name already exists.")
        return name
    
    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get('thumbnail')
        if thumbnail:
            if thumbnail.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("Image file too large. Maximum size is 5MB.")
            if not thumbnail.content_type.startswith('image/'):
                raise forms.ValidationError("File must be an image.")
        return thumbnail