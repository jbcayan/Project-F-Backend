"""Helper functions for common tasks"""""
import re
from django.core.exceptions import ValidationError

def validate_password_complexity(value):
    """Validate that the password is at least 8 characters long
    and contains one Upper case letter, one lower case letter, one number"""
    errors = []
    if len(value) < 8:
        errors.append("at least 8 characters")
    if re.search(r"\d", value) is None:
        errors.append("one number")
    if re.search(r"[A-Z]", value) is None:
        errors.append("one uppercase letter")
    if re.search(r"[a-z]", value) is None:
        errors.append("one lowercase letter")
    if errors:
        raise ValidationError("Password must contain: " + ", ".join(errors) + ".")