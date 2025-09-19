# authenticate/signals.py
from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(pre_social_login)
def link_to_existing_user(sender, request, sociallogin, **kwargs):
    """
    Automatically connect a social account to an existing user
    with the same email.
    """
    email = sociallogin.account.extra_data.get("email")
    if email:
        try:
            user = User.objects.get(email=email)
            # This links the social account with the existing user
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
