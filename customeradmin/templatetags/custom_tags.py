from django import template
from customeradmin.utils import get_best_offer_for_product

register = template.Library()

@register.simple_tag
def best_offer_for_product(product):
    offer, disc = get_best_offer_for_product(product)
    if offer:
        return {'offer': offer, 'discount': disc, 'final_price': product.price - disc}
    return None