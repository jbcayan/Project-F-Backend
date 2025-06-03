from django.db import models
from django.contrib.auth import get_user_model
from gallery.choices import FileTypes, RequestStatus
from common.models import BaseModelWithUID

User = get_user_model()

# Create your models here.
class Gallery(BaseModelWithUID):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name='created_galleries'
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name='updated_galleries'
    )
    file_type = models.CharField(
        max_length=10,
        choices=FileTypes,
        default=FileTypes.OTHER
    )
    file = models.FileField(upload_to='media/')
    is_public = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)


class EditRequest(BaseModelWithUID):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='edit_requests'
    )
    media_file = models.ForeignKey(
        Gallery,
        on_delete=models.CASCADE,
        related_name='edit_requests'
    )
    description = models.TextField(
        help_text='Please describe the changes you want to make'
    )
    request_status = models.CharField(
        max_length=20,
        choices=RequestStatus,
        default=RequestStatus.PENDING
    )
    response_file = models.FileField(upload_to='responses/', null=True, blank=True)
