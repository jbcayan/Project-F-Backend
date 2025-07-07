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


class FileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = EditRequestGallery
        fields = [
            "file",
        ]

    def get_file(self, obj):
        request_type = obj.edit_request.request_type

        if request_type == RequestType.SOUVENIR_REQUEST:
            return obj.gallery.file.url if obj.gallery and obj.gallery.file else None
        return obj.user_request_file.url if obj.user_request_file else None

class DownloadSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True, source='request_files')

    class Meta:
        model = EditRequest
        fields = [
            "uid",
            "title",
            "code",
            "description",
            "special_note",
            "request_status",
            'request_type',
            "desire_delivery_date",
            "shipping_address",
            "additional_notes",
            "files",
            "created_at",
        ]
