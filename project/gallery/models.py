"""Gallery models for the system."""""

from django.contrib.auth import get_user_model
from django.db import models

from common.helpers import unique_file_code, unique_request_code
from common.models import BaseModelWithUID
from gallery.choices import FileTypes, RequestStatus, RequestType

User = get_user_model()

# Create your models here.
class Gallery(BaseModelWithUID):
    title = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        db_index=True
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name='created_galleries',
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name='updated_galleries',
        null=True,
        blank=True
    )
    file_type = models.CharField(
        max_length=10,
        choices=FileTypes,
        default=FileTypes.OTHER
    )
    file = models.FileField(upload_to='gallery/')
    is_public = models.BooleanField(default=False)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

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



# ====================================================
# Like Cart
# ====================================================
class EditRequest(BaseModelWithUID):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name='submitted_edit_requests'
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        db_index=True
    )
    media_files = models.ManyToManyField(
        "Gallery",
        through='EditRequestGallery',
        related_name='edit_requests',
        blank=True,
    )
    title = models.CharField(
        max_length=255,
        help_text='Please provide a title for the request',
        blank=True,
        null=True
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
    shipping_address = models.TextField(
        help_text='Please provide the shipping address',
        blank=True,
        null=True
    )
    additional_notes = models.TextField(
        help_text='Please provide any additional notes',
        blank=True,
        null=True
    )
    request_type = models.CharField(
        max_length=20,
        choices=RequestType,
        default=RequestType.OTHER,
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_request_code(self.request_type)
        super(EditRequest, self).save(*args, **kwargs)

    def __str__(self):
        return f"Edit Request by {self.user} - {self.pk}"

    class Meta:
        verbose_name = "Edit Request"
        verbose_name_plural = "Edit Requests"
        ordering = ('-created_at',)



# ====================================================
# Like Cart Items
# ====================================================
class EditRequestGallery(models.Model):
    edit_request = models.ForeignKey(
        "EditRequest",
        on_delete=models.CASCADE,
        related_name='request_files'
    )
    gallery = models.ForeignKey(
        "Gallery",
        on_delete=models.CASCADE,
        related_name='requested_in',
        blank=True,
        null=True,
        help_text='Please select the gallery you would like to edit'
    )
    file_type = models.CharField(
        max_length=10,
        choices=FileTypes,
        default=FileTypes.OTHER
    )
    user_request_file = models.FileField(
        upload_to='user-requests/',
        blank=True,
        null=True,
        help_text='Please upload the file you would like to edit'
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
    quantity = models.IntegerField(
        default=1,
        blank=True,
        null=True,
        help_text='Quantity of files to be edited or ordered'
    )

    class Meta:
        unique_together = ('edit_request', 'gallery')

    def __str__(self):
        return f"{self.edit_request} | {self.edit_request.user}"


    class Meta:
        verbose_name = "Edit Request Gallery"
        verbose_name_plural = "Edit Request Galleries"
        ordering = ('-edit_request__created_at',)


