from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect

from django.contrib import messages
from .models import (
    CustomUser,
    UserAddress,
    Order,
    OrderItem,
    OrderStatusHistory,
    Cart,
    CartItem,
    Wishlist,
    WishlistItem,
    Wallet,
    WalletTransaction,
)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'full_name', 'phone_number', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions')
        }),
        ('Important dates', {'fields': ('created_at',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'phone_number',
                'password1',
                'password2',
                'is_staff',
                'is_superuser',
                'is_active',
            ),
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "state", "country", "is_default")
    search_fields = ("user__email", "city")

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib import messages
from authenticate.models import Order, Wallet   # keep your other imports


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "status",
        "payment_status",
        "total_amount",
        "created_at",
        "refund_action",          # clickable helper
    )
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("order_number", "user__email")
    readonly_fields = ("razorpay_order_id", "razorpay_payment_id")
    actions = ["refund_cancelled_auto", "refund_returned_pending"]

    # ---------- ACTION ----------
    def refund_cancelled_auto(self, request, queryset):
        for order in queryset.filter(status='cancelled', payment_status__in=['paid', 'refunded']):
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            if order.total_amount > 0:
                wallet.credit(
                    order.total_amount,
                    order,
                    "Auto-refund for cancelled order"
                )

        self.message_user(request, "Cancelled orders refunded to wallets instantly.")
        return redirect("customeradmin:order-list")


    # ---------- ACTION ----------
    def refund_returned_pending(self, request, queryset):
        """Mark delivered orders as refund-pending (admin will confirm)."""
        updated = queryset.filter(status='delivered').update(status='refund_pending')
        self.message_user(request, f"{updated} delivered orders marked as ‘Refund Pending’.")
        return redirect("customeradmin:order-list")

    # ---------- LIST-COLUMN ----------
    def refund_action(self, obj):
        if obj.status == 'refund_pending':
            url = reverse('customeradmin:return_requests_list')
            return format_html(
                '<a class="button" href="{}">Verify & Refund</a>', url
            )
        return "-"
    refund_action.short_description = "Refund Action"

    # ---------- TEMPLATE HACK (optional) ----------
    # If you want the button styled like a real Django button:
    change_list_template = "orders/change_list.html" 


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "quantity", "total_price")
    search_fields = ("product_name",)


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "old_status", "new_status", "changed_at")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "total_items", "total_amount")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("wishlist", "product")



# ---------- WALLET ADMIN ----------
class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ('txn_type', 'amount', 'order', 'note', 'created_at')   # ← txn_type
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')                    # ← removed created_at
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('balance',)
    inlines = [WalletTransactionInline]

    def has_add_permission(self, request):
        return False


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'txn_type', 'amount', 'order', 'created_at')   # ← txn_type
    list_filter = ('txn_type', 'created_at')                                  # ← txn_type
    search_fields = ('wallet__user__email', 'order__order_number')
    readonly_fields = ('wallet', 'order', 'amount', 'txn_type', 'note', 'created_at')  # ← txn_type

    def has_add_permission(self, request):
        return False