from django.core.management.base import BaseCommand
from django.db import models
from authenticate.models import Order


class Command(BaseCommand):
    help = 'Fix orders where discount_amount incorrectly duplicates coupon_discount'

    def handle(self, *args, **options):
        # Find all orders where discount_amount equals coupon_discount and both are > 0
        problematic_orders = Order.objects.filter(
            discount_amount__gt=0,
            coupon_discount__gt=0,
            discount_amount=models.F('coupon_discount')
        )
        
        count = problematic_orders.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No problematic orders found!'))
            return
        
        self.stdout.write(f'Found {count} orders with duplicate discounts')
        
        # Fix them by setting discount_amount to 0
        updated = problematic_orders.update(discount_amount=0)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {updated} orders!')
        )
        
        # Show summary of fixed orders
        self.stdout.write('\nFixed orders:')
        for order in Order.objects.filter(id__in=problematic_orders.values_list('id', flat=True)):
            self.stdout.write(
                f'  Order {order.order_number}: '
                f'Coupon Discount: ₹{order.coupon_discount}, '
                f'Discount: ₹{order.discount_amount}'
            )
