from celery import shared_task
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

from gallery.models import EditRequest, EditRequestGallery


@shared_task
def handle_edit_request_file(edit_request_id, files_data):
    edit_request = EditRequest.objects.get(id=edit_request_id)
    for file_data in files_data:
        with default_storage.open(file_data['path'], 'rb') as f:
            django_file = File(f, name=file_data['path'].split('/')[-1])
            EditRequestGallery.objects.create(
                edit_request=edit_request,
                user_request_file=django_file,
                file_type=file_data['file_type']
            )

    return "Edit request processed successfully."


@shared_task()
def print_something():
    print("Hello, world!")

@shared_task
def send_mail_task(subject, text_content, html_content, to_email):
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()