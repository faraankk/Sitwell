from PIL import Image
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from decimal import Decimal
from django.utils import timezone
from .models import Offer, ProductOffer, CategoryOffer

def process_image(uploaded_file, max_width=800, max_height=600, quality=85, crop=True):
    try:
        img = Image.open(uploaded_file)
        
        
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        if crop:
            
            img = smart_crop_resize(img, target_width=max_width, target_height=max_height)
        else:
            
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        y
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        
        original_name = uploaded_file.name
        new_name = f"{original_name.split('.')[0]}.jpg"
        
        return InMemoryUploadedFile(
            output, 'ImageField', new_name, 'image/jpeg',
            sys.getsizeof(output), None
        )
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return uploaded_file


def smart_crop_resize(img, target_width, target_height):
    original_width, original_height = img.size
    target_ratio = target_width / target_height
    original_ratio = original_width / original_height
    
    if original_ratio > target_ratio:
        
        new_width = int(original_height * target_ratio)
        offset = (original_width - new_width) // 2
        img = img.crop((offset, 0, offset + new_width, original_height))
    elif original_ratio < target_ratio:
        
        new_height = int(original_width / target_ratio)
        offset = (original_height - new_height) // 2
        img = img.crop((0, offset, original_width, offset + new_height))
    
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return img


def crop_image(image_data, crop_data):
    
    try:
        img = Image.open(io.BytesIO(image_data))
        
        x = int(crop_data.get('x', 0))
        y = int(crop_data.get('y', 0))
        width = int(crop_data.get('width', img.width))
        height = int(crop_data.get('height', img.height))
        
        box = (x, y, x + width, y + height)
        cropped_img = img.crop(box)
        
        output = io.BytesIO()
        cropped_img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        print(f"Error cropping image: {str(e)}")
        return image_data
    

from decimal import Decimal
from .models import Offer, ProductOffer, CategoryOffer

def get_best_offer_for_product(product):
    """
    Returns (offer_object, discount_amount) that gives highest discount for the product.
    If no offers -> (None, 0)
    """
    price = product.price
    now = timezone.now()

    prod_offers = ProductOffer.objects.filter(
        products=product,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now
    ).select_related('offer')

    cat_offers = CategoryOffer.objects.filter(
        category=product.category,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now
    ).select_related('offer')

    best_offer = None
    best_disc = Decimal('0')

    for po in prod_offers:
        disc = po.offer.calculate_discount(raw_price=price)
        if disc > best_disc:
            best_disc = disc
            best_offer = po.offer

    for co in cat_offers:
        disc = co.offer.calculate_discount(raw_price=price)
        if disc > best_disc:
            best_disc = disc
            best_offer = co.offer

    return best_offer, best_disc