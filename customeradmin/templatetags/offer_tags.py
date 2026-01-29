# sitwell/templatetags/offer_tags.py
from django import template
from django.utils import timezone
from customeradmin.models import ProductOffer, CategoryOffer

register = template.Library()

@register.simple_tag
def best_offer_for_product(product):
    now = timezone.now()

    # 1. product-specific offers (M2M reverse)
    product_offers = ProductOffer.objects.filter(
        products=product,                 # <- use the M2M manager
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now
    ).select_related('offer').order_by('-offer__discount_value')

    # 2. category offers (same as before)
    category_offers = CategoryOffer.objects.filter(
        category=product.category,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now
    ).select_related('offer').order_by('-offer__discount_value')

    best = None
    best_price = product.price

    if product_offers.exists():
        best = product_offers.first().offer
    elif category_offers.exists():
        best = category_offers.first().offer

    if best:
        best_price = product.get_discounted_price(offer=best)

    return {'offer': best, 'final': best_price}