import random
from datetime import timedelta, datetime

from django.db.models import Q
from django.utils.timezone import now, make_aware

from accounts.models import OTP
# from payment_service.models import UserSubscription, SubscriptionStatus
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from payment_service.models import PaymentHistory



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

# def is_user_subscribed(user):
#     try:
#         subscription = user.subscription
#     except UserSubscription.DoesNotExist:
#         return False
#
#     if (
#         subscription.status == SubscriptionStatus.ACTIVE and
#         # not subscription.cancel_at_period_end and
#         subscription.current_period_end and
#         subscription.current_period_end > now()
#     ):
#         return True
#
#     return False


def has_premium_access(user):
    """
        Check if user has premium access based on subscription status and expiry dates.
        Users should have premium access until their paid period expires.
    """
    subscription = PaymentHistory.objects.filter(
        user=user).filter(
        Q(payment_type='recurring') | Q(payment_type='one_time')
    ).order_by('-created_at').first()


    from datetime import timedelta, date

    current_time = now()

    try:
        # If subscription is cancelled, check if we're still within the paid period
        if subscription.status == 'canceled':
            # For cancelled subscriptions, check if we're still within the current billing period
            if subscription.cancelled_on:
                # Calculate the end of the current billing period
                period_end = get_access_expiry_date(subscription)
                if period_end:
                    # Ensure both are datetime objects for comparison
                    if isinstance(period_end, date) and not isinstance(period_end, datetime):
                        period_end = make_aware(datetime.combine(period_end, datetime.min.time()))

                    if current_time < period_end:
                        return True
            return False

        # If subscription failed or expired, no access
        if subscription.status in ['failed', 'expired']:
            return False

        # For active subscriptions, check if we're within the current period
        if subscription.status in ['current', 'active', 'unverified']:
            # For 'current' status, user should have premium access
            if subscription.status == 'current':
                return True

            # For 'active' status, check if we're within the current billing period
            if subscription.status == 'active':
                period_end = get_access_expiry_date(subscription)
                if period_end:
                    # Ensure both are datetime objects for comparison
                    if isinstance(period_end, date) and not isinstance(period_end, datetime):
                        period_end = make_aware(datetime.combine(period_end, datetime.min.time()))

                    if current_time < period_end:
                        print(
                            f"[DEBUG] SubscriptionStatusView._has_premium_access - Active subscription within period until {period_end}")
                        return True

            # For unverified subscriptions, give 24 hours grace period
            if subscription.status == 'unverified':
                if subscription.created_at and (current_time - subscription.created_at) < timedelta(hours=24):
                    print(
                        f"[DEBUG] SubscriptionStatusView._has_premium_access - Unverified but within 24h grace period")
                    return True
    except:
        return False

    return False

def get_access_expiry_date(subscription):
    """
    Calculate when the user's premium access expires based on subscription details.
    """
    from datetime import date

    # If subscription is cancelled, access expires at the end of current billing period
    if subscription.status == 'canceled' and subscription.cancelled_on:
        # For cancelled subscriptions, access continues until the end of the current period
        # We need to calculate when the current period would have ended
        if subscription.next_payment_due_date:
            expiry_date = subscription.next_payment_due_date
            # Ensure it's a datetime object
            if isinstance(expiry_date, date) and not isinstance(expiry_date, datetime):
                expiry_date = make_aware(datetime.combine(expiry_date, datetime.min.time()))
            return expiry_date
        else:
            # Fallback: add one billing period from creation date
            return calculate_next_billing_date(subscription.created_at, subscription.period)

    # For active subscriptions, access expires at next payment due date
    if subscription.next_payment_due_date:
        expiry_date = subscription.next_payment_due_date
        # Ensure it's a datetime object
        if isinstance(expiry_date, date) and not isinstance(expiry_date, datetime):
            expiry_date = make_aware(datetime.combine(expiry_date, datetime.min.time()))
        return expiry_date

    # Fallback: calculate based on creation date and period
    if subscription.created_at and subscription.period:
        return calculate_next_billing_date(subscription.created_at, subscription.period)

    return None


def calculate_next_billing_date(self, start_date, period):
    """
    Calculate the next billing date based on start date and period.
    """
    from datetime import timedelta, date

    if not start_date:
        return None

    # Ensure start_date is a datetime object
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = make_aware(datetime.combine(start_date, datetime.min.time()))

    if period == 'daily':
        return start_date + timedelta(days=1)
    elif period == 'weekly':
        return start_date + timedelta(weeks=1)
    elif period == 'monthly':
        # Add approximately one month (30 days)
        return start_date + timedelta(days=30)
    elif period == 'yearly':
        return start_date + timedelta(days=365)
    else:
        # Default to monthly
        return start_date + timedelta(days=30)


def generate_password_reset_token_url(user):
    uid64 = urlsafe_base64_encode(force_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)
    return f"{settings.FRONTEND_URL}/reset-password/{uid64}/{token}"

