from django.contrib import admin
from .models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


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
    inlines = [ProductImageInline]

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
            'fields': ('short_description', 'long_description', 'features')
        }),
        ('Specifications', {
            'fields': ('dimensions', 'weight', 'material', 'color_options')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
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

