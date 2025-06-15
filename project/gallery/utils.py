import mimetypes
import os
from rest_framework.exceptions import ValidationError
from gallery.choices import FileTypes


def validate_file_matches_type(file, file_type):
    if file_type == FileTypes.OTHER or not file:
        return  # Skip validation for "other" or missing file

    extension = os.path.splitext(file.name)[1].lower()
    mime_type, _ = mimetypes.guess_type(file.name)

    expected_mime_prefix = {
        FileTypes.IMAGE: 'image',
        FileTypes.AUDIO: 'audio',
        FileTypes.VIDEO: 'video',
        FileTypes.PDF: 'application/pdf',
        FileTypes.DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        FileTypes.PPTX: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        FileTypes.XLSX: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }

    expected = expected_mime_prefix.get(file_type)
    if expected:
        if not mime_type or not mime_type.startswith(expected):
            raise ValidationError(
                f"Uploaded file type ('{mime_type}') does not match the declared file_type '{file_type}'."
            )