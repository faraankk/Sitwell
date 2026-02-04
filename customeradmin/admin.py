from django.contrib import admin
from .models import Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['material', 'sku_suffix', 'price_adjustment', 'stock_quantity', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'stock_quantity',
        'status',
        'is_blocked',
        'created_at',
    )

    list_filter = ('category', 'status', 'is_blocked', 'created_at')
    search_fields = ('name', 'sku', 'brand')
    actions = ['block_selected_products', 'unblock_selected_products']
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'sku', 'category', 'brand')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_type', 'discount_value')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold')
        }),
        ('Status', {
            'fields': ('status', 'is_blocked')
        }),
        ('Descriptions', {
            'fields': ('short_description', 'detailed_description')
        }),
        ('Tax', {
            'fields': ('tax_type', 'vat_percentage')
        }),
    )

    def block_selected_products(self, request, queryset):
        updated = queryset.update(is_blocked=True)
        self.message_user(request, f'{updated} product(s) successfully blocked.')

    block_selected_products.short_description = 'Block selected products'

    def unblock_selected_products(self, request, queryset):
        updated = queryset.update(is_blocked=False)
        self.message_user(request, f'{updated} product(s) successfully unblocked.')

    unblock_selected_products.short_description = 'Unblock selected products'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'full_sku', 'material', 'stock_quantity', 'price_adjustment', 'is_active']
    list_filter = ['is_active', 'product__category', 'material']
    search_fields = ['product__name', 'product__sku', 'material']
    list_editable = ['stock_quantity', 'is_active']
    autocomplete_fields = ['product']
    
    fieldsets = (
        ('Product', {
            'fields': ('product',)
        }),
        ('Variant Attributes', {
            'fields': ('material', 'sku_suffix')
        }),
        ('Pricing & Stock', {
            'fields': ('price_adjustment', 'stock_quantity')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def full_sku(self, obj):
        return obj.full_sku
    full_sku.short_description = 'SKU'


from .models import (
    Offer, ProductOffer, CategoryOffer, ReferralOffer,
    Referral, ReferralUsage
)

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'offer_type', 'discount_value', 'start_date', 'end_date', 'is_active')
    list_filter = ('offer_type', 'is_active', 'start_date', 'end_date')
    search_fields = ('name',)

class ProductOfferInline(admin.TabularInline):
    model = ProductOffer.products.through
    extra = 1

@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = ('offer',)
    inlines = [ProductOfferInline]

@admin.register(CategoryOffer)
class CategoryOfferAdmin(admin.ModelAdmin):
    list_display = ('offer', 'category')

@admin.register(ReferralOffer)
class ReferralOfferAdmin(admin.ModelAdmin):
    list_display = ('offer', 'referrer_reward', 'referee_reward')

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'code', 'created_at')
    search_fields = ('referrer__email', 'code')

@admin.register(ReferralUsage)
class ReferralUsageAdmin(admin.ModelAdmin):
    list_display = ('referral', 'referee', 'used_at')


from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'status', 'is_active', 'order', 'clicks', 'impressions', 'start_date', 'end_date']
    list_filter = ['position', 'status', 'created_at']
    search_fields = ['title', 'heading', 'subheading']
    list_editable = ['order', 'status']
    readonly_fields = ['clicks', 'impressions', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'position', 'status', 'order')
        }),
        ('Images', {
            'fields': ('image', 'mobile_image'),
            'description': 'Recommended sizes: Hero banner 1920x600px, Mobile banner 768x400px'
        }),
        ('Content', {
            'fields': ('heading', 'subheading', 'button_text', 'button_link')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
        ('Analytics', {
            'fields': ('clicks', 'impressions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'