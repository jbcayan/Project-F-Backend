import random
from datetime import timedelta, datetime

from django.utils.timezone import now

from accounts.models import OTP
from payment_service.models import UserSubscription, SubscriptionStatus


def generate_unique_otp(length=6) -> str:
    otp = "".join(random.choices("0123456789", k=length))

    return otp

def check_otp_validity(user_otp):
    """
    Check given otp is not expired 24 hours
    :param user_otp:
    :return:
    """
    # Check if otp is valid for 24 hours
    otp = OTP.objects.filter(
        otp=user_otp,
        created_at__gte=(datetime.now() - timedelta(hours=24)),
    ).first()

    if not otp:
        return False

    return True

def is_user_subscribed(user):
    try:
        subscription = user.subscription
    except UserSubscription.DoesNotExist:
        return False

    if (
        subscription.status == SubscriptionStatus.ACTIVE and
        # not subscription.cancel_at_period_end and
        subscription.current_period_end and
        subscription.current_period_end > now()
    ):
        return True

    return False



