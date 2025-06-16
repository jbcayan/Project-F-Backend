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

class RequestType(TextChoices):
    PHOTO_REQUEST = 'photo_request', 'Photo Request'
    VIDEO_REQUEST = 'video_request', 'Video Request'
    AUDIO_REQUEST = 'audio_request', 'Audio Request'
    SOUVENIR_REQUEST = 'souvenir_request', 'Souvenir Request'
    OTHER = 'other', 'Other'

class EditType(TextChoices):
    PHOTO_EDITING = 'photo_editing', 'Photo Editing'
    VIDEO_EDITING = 'video_editing', 'Video Editing'
    AUDIO_EDITING = 'audio_editing', 'Audio Editing'
    SOUVENIR_EDITING = 'souvenir_editing', 'Souvenir Editing'
    OTHER = 'other', 'Other'