from django.apps import AppConfig


class AuthenticateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authenticate'


# authenticate/apps.py
from django.apps import AppConfig


class AuthenticateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authenticate"

    def ready(self):
        import authenticate.signals  # 👈 ensures signals are loaded
