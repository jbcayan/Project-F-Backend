from django.db.models import TextChoices


class FileTypes(TextChoices):
    IMAGE = 'image', 'Image'
    AUDIO = 'audio', 'Audio'
    VIDEO = 'video', 'Video'
    PDF = 'pdf', 'PDF'
    DOCX = 'docx', 'DOCX'
    PPTX = 'pptx', 'PPTX'
    XLSX = 'xlsx', 'XLSX'
    OTHER = 'other', 'Other'


class RequestStatus(TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    REJECTED = 'rejected', 'Rejected'