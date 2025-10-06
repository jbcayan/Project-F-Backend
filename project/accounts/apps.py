from django.apps import AppConfig
from django.conf import settings
import os
from typing import List, Tuple
from django.db.models.signals import post_migrate


def _load_test_users_from_env() -> List[Tuple[str, str]]:
    """Load test payment users from env.
    Supported formats:
      - Preferred: TEST_PAYMENT_USERS="email1:pass1,email2:pass2"
      - Back-compat: TEST_PAYMENT_USERS="email1,email2" + TEST_PAYMENT_PASSWORD applies to all
      - Legacy: TEST_Payment_USERS also supported
    """
    raw = os.getenv('TEST_PAYMENT_USERS') or os.getenv('TEST_Payment_USERS') or ''
    default_password = os.getenv('TEST_PAYMENT_PASSWORD', 'ProjectF@2025')
    entries = [e.strip() for e in raw.split(',') if e.strip()]
    pairs: List[Tuple[str, str]] = []
    for entry in entries:
        if ':' in entry:
            email, pwd = entry.split(':', 1)
            email = email.strip()
            pwd = pwd.strip()
            if email:
                pairs.append((email, pwd or default_password))
        else:
            pairs.append((entry, default_password))
    return pairs


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Ensure test users are created right after migrations complete
        def _create_test_users(sender, **kwargs):
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()

                for email, password in _load_test_users_from_env():
                    try:
                        user, created = User.objects.get_or_create(email=email)
                        if created:
                            user.set_password(password)
                            user.is_verified = True
                            if hasattr(user, 'updated_at'):
                                user.save(update_fields=["password", "is_verified", "updated_at"])
                            else:
                                user.save()
                    except Exception:
                        continue
            except Exception:
                # Do not fail migrations if user creation fails
                pass

        post_migrate.connect(_create_test_users, sender=self)

        # Best-effort attempt during app startup as well (in case running without migrate step)
        try:
            _create_test_users(sender=self)
        except Exception:
            pass
