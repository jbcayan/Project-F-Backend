from django.db.models import TextChoices


class Status(TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DRAFT = "DRAFT", "DRAFT"
    INACTIVE = "INACTIVE", "Inactive"
    REMOVED = "REMOVED", "Removed"


class UserKind(TextChoices):
    ADMIN = "ADMIN", "Admin"
    END_USER = "END_USER", "End User"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    UNDEFINED = "UNDEFINED", "Undefined"


class UserGender(TextChoices):
    FEMALE = "FEMALE", "Female"
    MALE = "MALE", "Male"
    UNKNOWN = "UNKNOWN", "Unknown"
    OTHER = "OTHER", "Other"


class ResetStatus(TextChoices):
    FAILED = "FAILED", "Failed"
    SUCCESS = "SUCCESS", "Success"
    PENDING = "PENDING", "Pending"


class ResetType(TextChoices):
    SELF = "SELF", "Self"
    MANUAL = "MANUAL", "Manual"


class OtpType(TextChoices):
    PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
    PHONE_NUMBER_RESET = "PHONE_NUMBER_RESET", "Phone Number Reset"
    OTHER = "OTHER", "Other"