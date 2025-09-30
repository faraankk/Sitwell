from django.core.management.base import BaseCommand
from authenticate.models import CustomUser, UserAddress
from authenticate.utils import clean_phone_number


class Command(BaseCommand):
    help = 'Clean all existing phone numbers in database'

    def handle(self, *args, **options):
        self.stdout.write("Starting phone number cleanup...")
        
        # Clean CustomUser phone numbers
        users_updated = 0
        for user in CustomUser.objects.all():
            if user.phone_number:
                old_number = user.phone_number
                cleaned_number = clean_phone_number(user.phone_number)
                if old_number != cleaned_number:
                    user.phone_number = cleaned_number
                    user.save()
                    users_updated += 1
                    self.stdout.write(f"Updated user {user.email}: '{old_number}' -> '{user.phone_number}'")

        # Clean UserAddress phone numbers
        addresses_updated = 0
        for address in UserAddress.objects.all():
            if address.phone_number:
                old_number = address.phone_number
                cleaned_number = clean_phone_number(address.phone_number)
                if old_number != cleaned_number:
                    address.phone_number = cleaned_number
                    address.save()
                    addresses_updated += 1
                    self.stdout.write(f"Updated address {address.id}: '{old_number}' -> '{address.phone_number}'")

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully cleaned {users_updated} user phone numbers and {addresses_updated} address phone numbers'
            )
        )
        
        if users_updated == 0 and addresses_updated == 0:
            self.stdout.write(
                self.style.WARNING("No phone numbers needed cleaning - all are already in correct format")
            )
