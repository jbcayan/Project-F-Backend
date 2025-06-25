"""Helper functions for common tasks"""""

import random
import re
import string

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


def generate_code():
    alphabet = string.ascii_uppercase  # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    prefix = ''.join(random.choices(alphabet, k=4))
    number = str(random.randint(1000, 9999)).zfill(7)
    return f"{prefix}-{number}"


def unique_file_code():
    from gallery.models import Gallery

    code = generate_code()
    while Gallery.objects.filter(code=code).exists():
        code = generate_code()
    return f"GL-{code}"

def unique_request_code(request_type):
    from gallery.models import EditRequest

    code = generate_code()
    while EditRequest.objects.filter(code=code).exists():
        code = generate_code()
    return f"{request_type}-{code}"
