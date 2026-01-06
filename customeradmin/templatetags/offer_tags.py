from django import template
from customeradmin.utils import get_best_offer_for_product
from decimal import Decimal

register = template.Library()

@register.simple_tag
def best_offer_for_product(product):
    """
    Returns dict with keys:
      offer   – the Offer instance (None if none)
      discount– Decimal discount amount
      final   – Decimal price after discount
    """
    offer, disc = get_best_offer_for_product(product)
    return {
        'offer': offer,
        'discount': disc,
        'final': max(Decimal('0'), product.price - disc)
    }