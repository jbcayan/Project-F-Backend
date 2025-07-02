from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from accounts.models import OTP, User  # Adjust import paths as needed


@shared_task
def delete_used_or_expired_otps():
    """Deletes OTPs that are either used or older than 24 hours (expired)."""
    threshold = timezone.now() - timedelta(hours=24)

    deleted_count, _ = OTP.objects.filter(
        Q(is_used=True) | Q(created_at__lt=threshold)
    ).delete()

    return f"Deleted {deleted_count} used or expired OTPs."


@shared_task
def delete_unverified_users():
    """Deletes users who are not verified and were created more than 24 hours ago."""
    threshold = timezone.now() - timedelta(hours=24)
    deleted_count, _ = User.objects.filter(
        is_verified=False,
        created_at__lt=threshold
    ).delete()
    return f"Deleted {deleted_count} unverified users."
