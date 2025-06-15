from rest_framework import serializers

from common.choices import Status
from gallery.models import Gallery, EditRequest, EditRequestGallery
from gallery.utils import validate_file_matches_type


class GalleryUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = [
            "uid",
            "title",
            "code",
            "description",
            "status",
            "file_type",
            "file",
        ]
        read_only_fields = ["uid", "status"]

    def validate(self, attrs):
        validate_file_matches_type(attrs.get('file'), attrs.get('file_type'))
        return attrs
