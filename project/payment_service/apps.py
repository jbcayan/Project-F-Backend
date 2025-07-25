from django.apps import AppConfig


class PaymentServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payment_service'

    def ready(self):
        import payment_service.signals
