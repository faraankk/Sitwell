
from django import template
from django.utils import timezone
from django.template import Context, Template          # NEW
from customeradmin.models import Banner
from django.db.models import Q

register = template.Library()

@register.inclusion_tag('authenticate/banners.html', takes_context=True)   # NEW
def get_banners(context, position='hero'):                                 # NEW
    now = timezone.now()
    banners = Banner.objects.filter(
        status='active',
        position=position,
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).order_by('order', '-created_at')

    for b in banners:
        if b.button_link:
            b.button_link = Template(b.button_link).render(Context(context))

    return {'banners': banners, 'position': position}