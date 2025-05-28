""" User models for the system. """
from django.contrib.auth.base_user import (
    BaseUserManager,
)
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.db import models
from django.db.models.signals import post_save

from accounts.signals import post_save_create_profile_receiver
from common.choices import UserKind, UserGender
from common.models import BaseModelWithUID
from common.utils import get_user_media_path_prefix


class UserManager(BaseUserManager):
    """Managers for users."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have a email address")

        email = self.normalize_email(email)

        user = self.model(
            email=email, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """Create a new superuser and return superuser"""

        user = self.create_user(
            email=email, password=password
        )
        user.is_superuser = True
        user.is_staff = True
        user.kind = UserKind.SUPER_ADMIN
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, BaseModelWithUID, PermissionsMixin):
    """Users in the System"""

    email = models.EmailField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_staff = models.BooleanField(
        default=False,
    )
    kind = models.CharField(
        max_length=20,
        choices=UserKind.choices,
        default=UserKind.UNDEFINED,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "System User"
        verbose_name_plural = "System Users"



class UserProfile(models.Model):
    """Profile for a user"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    full_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    image = models.ImageField(
        upload_to=get_user_media_path_prefix,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.full_name if self.full_name else self.user.email


post_save.connect(post_save_create_profile_receiver, sender=User)