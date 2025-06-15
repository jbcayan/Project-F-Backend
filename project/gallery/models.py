"""Gallery models for the system."""""

from django.contrib.auth import get_user_model
from django.db import models

from common.helpers import unique_file_code, unique_request_code
from common.models import BaseModelWithUID
from gallery.choices import FileTypes, RequestStatus

User = get_user_model()

# Create your models here.
class Gallery(BaseModelWithUID):
    title = models.CharField(max_length=255)
    code = models.CharField(
        max_length=15,
        unique=True,
        editable=False,
        db_index=True
    )
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
    file = models.FileField(upload_to='gallery/')
    is_public = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_file_code()
        super(Gallery, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - ({self.code})"

    class Meta:
        verbose_name = "Gallery"
        verbose_name_plural = "Galleries"
        ordering = ('-created_at',)


class EditRequest(BaseModelWithUID):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name='submitted_edit_requests'
    )
    code = models.CharField(
        max_length=15,
        unique=True,
        editable=False,
        db_index=True
    )
    media_files = models.ManyToManyField(
        "Gallery",
        through='EditRequestGallery',
        related_name='edit_requests'
    )
    description = models.TextField(
        help_text='Please describe the overall request'
    )
    special_note = models.TextField(
        help_text='Please add any special notes',
        null=True,
        blank=True
    )
    request_status = models.CharField(
        max_length=20,
        choices=RequestStatus,
        default=RequestStatus.PENDING
    )
    desire_delivery_date = models.DateTimeField(
        help_text='When would you like the changes delivered?'
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_request_code()
        super(EditRequest, self).save(*args, **kwargs)

    def __str__(self):
        return f"Edit Request by {self.user} - {self.pk}"

    class Meta:
        verbose_name = "Edit Request"
        verbose_name_plural = "Edit Requests"
        ordering = ('-created_at',)

class EditRequestGallery(models.Model):
    edit_request = models.ForeignKey(
        "EditRequest",
        on_delete=models.CASCADE,
        related_name='request_files'
    )
    gallery = models.ForeignKey(
        "Gallery",
        on_delete=models.CASCADE,
        related_name='requested_in'
    )
    individual_note = models.TextField(
        blank=True,
        null=True,
        help_text='Specific instructions for this file (optional)'
    )
    file_status = models.CharField(
        max_length=20,
        choices=RequestStatus,
        default=RequestStatus.PENDING
    )
    admin_response_file = models.FileField(upload_to='responses/', null=True, blank=True)
    responded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='file_edit_responses'
    )

    class Meta:
        unique_together = ('edit_request', 'gallery')

    def __str__(self):
        return f"{self.edit_request} | {self.gallery.code}"


    class Meta:
        verbose_name = "Edit Request Gallery"
        verbose_name_plural = "Edit Request Galleries"
        ordering = ('-edit_request__created_at',)


