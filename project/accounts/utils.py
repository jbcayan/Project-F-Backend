import random
from datetime import datetime, timedelta

from accounts.models import OTP


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



