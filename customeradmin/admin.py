from django.contrib import admin
from .models import Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_quantity', 'status', 'is_blocked', 'created_at')
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
            'fields': ('short_description', 'detailed_description')
        }),
        ('Blocking Info', {
            'fields': ('blocked_at', 'blocked_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('blocked_at', 'blocked_by')
    
    def block_selected_products(self, request, queryset):
        for product in queryset:
            product.block_product(blocked_by=request.user.username)
        self.message_user(request, f'{queryset.count()} products blocked successfully.')
    
    def unblock_selected_products(self, request, queryset):
        for product in queryset:
            product.unblock_product()
        self.message_user(request, f'{queryset.count()} products unblocked successfully.')
    
    block_selected_products.short_description = "Block selected products"
    unblock_selected_products.short_description = "Unblock selected products"
