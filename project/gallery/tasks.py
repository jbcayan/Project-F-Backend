from celery import shared_task
from django.core.files.base import File
from django.core.files.storage import default_storage

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


def send_request_completion_email(user, edit_request):
    # Logic to send email
    Subject = f"Your {edit_request.request_type} request has been completed!"