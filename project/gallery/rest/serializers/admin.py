from rest_framework import serializers

from common.choices import Status
from gallery.choices import RequestType
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
            "price",
        ]
        read_only_fields = ["uid", "status"]

    def validate(self, attrs):
        validate_file_matches_type(attrs.get('file'), attrs.get('file_type'))
        return attrs


class GalleryDetailSerializer(serializers.ModelSerializer):
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
            "price",
        ]
        read_only_fields = ["uid"]

    def validate(self, attrs):
        validate_file_matches_type(attrs.get('file'), attrs.get('file_type'))
        return attrs



class DownloadRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    request_type = serializers.ChoiceField(
        choices=RequestType.choices,
        required=True
    )
