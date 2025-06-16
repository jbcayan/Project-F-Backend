from rest_framework import serializers

from common.choices import Status
from gallery.models import Gallery, EditRequest, EditRequestGallery


class SimpleGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ["uid", "title", "code", "description", "file_type", "file"]

class EditRequestMinimalListSerializer(serializers.ModelSerializer):
    media_files = SimpleGallerySerializer(many=True, read_only=True)
    class Meta:
        model = EditRequest
        fields = ["uid", "description", "media_files"]

class EndUserEditRequestMediaFileSerializer(serializers.Serializer):
    gallery_uid = serializers.SlugRelatedField(
        queryset=Gallery.objects.filter(status=Status.ACTIVE),
        slug_field='uid',
        required=True,
        write_only=True,
        error_messages={
            'does_not_exist': 'Invalid or inactive gallery UID provided.'
        }
    )
    individual_note = serializers.CharField(required=False, allow_blank=True)


class EndUserEditRequestCreateSerializer(serializers.ModelSerializer):
    media_files = EndUserEditRequestMediaFileSerializer(
        many=True,
        write_only=True
    )

    class Meta:
        model = EditRequest
        fields = [
            'uid',
            'code',
            'media_files',
            'description',
            'special_note',
            'request_status',
            'desire_delivery_date',
        ]
        read_only_fields = [
            'uid',
            'code',
            'request_status',
        ]

    def create(self, validated_data):
        media_files = validated_data.pop('media_files')
        user = self.context['request'].user
        edit_request = EditRequest.objects.create(
            user=user,
            **validated_data
        )
        for media_file in media_files:
            EditRequestGallery.objects.create(
                edit_request=edit_request,
                gallery=media_file['gallery_uid'],
                individual_note=media_file['individual_note']
            )
        return edit_request



class EndUserEditRequestGalleryOutputSerializer(serializers.ModelSerializer):
    gallery_uid = serializers.UUIDField(source='gallery.uid', read_only=True)
    gallery_title = serializers.CharField(source='gallery.title', read_only=True)
    gallery_code = serializers.CharField(source='gallery.code', read_only=True)
    individual_note = serializers.CharField()
    file_status = serializers.CharField()
    admin_response_file = serializers.FileField()

    class Meta:
        model = EditRequestGallery
        fields = [
            "gallery_uid",
            "gallery_title",
            "gallery_code",
            "individual_note",
            "file_status",
            "admin_response_file"
        ]

class EndUserEditRequestRetrieveSerializer(serializers.ModelSerializer):
    request_files = EndUserEditRequestGalleryOutputSerializer(many=True, read_only=True)

    class Meta:
        model = EditRequest
        fields = [
            "uid",
            "description",
            "special_note",
            "request_status",
            "desire_delivery_date",
            "request_files"
        ]
