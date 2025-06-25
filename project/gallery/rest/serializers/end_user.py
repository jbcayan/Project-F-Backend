from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers

from common.choices import Status
from gallery.choices import FileTypes, RequestType, EditType, RequestStatus
from gallery.models import Gallery, EditRequest, EditRequestGallery
from gallery.tasks import handle_edit_request_file, send_mail_task


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
    # individual_note = serializers.CharField(required=False, allow_blank=True)


class EndUserEditRequestCreateSerializer(serializers.ModelSerializer):
    media_files = EndUserEditRequestMediaFileSerializer(
        many=True,
        write_only=True
    )
    quantity = serializers.IntegerField(required=True, write_only=True)  # Add write_only here

    class Meta:
        model = EditRequest
        fields = [
            'uid',
            'code',
            'media_files',
            'quantity',
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
        quantity = validated_data.pop('quantity')

        print(media_files[0]['gallery_uid'])

        user = self.context['request'].user
        edit_request = EditRequest.objects.create(
            user=user,
            request_type=RequestType.SOUVENIR_REQUEST,
            **validated_data
        )
        for media_file in media_files:
            file_type = media_file['gallery_uid'].file_type
            EditRequestGallery.objects.create(
                edit_request=edit_request,
                gallery=media_file['gallery_uid'],
                # individual_note=media_file['individual_note'],
                quantity=quantity,
                file_type=file_type
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

class SimpleFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditRequestGallery
        fields = [
            "file_type",
            "user_request_file",
            "file_status",
            "admin_response_file",
        ]

class PhotoEditRequestSerializer(serializers.ModelSerializer):
    request_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True
    )

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
        read_only_fields = [
            "uid",
            "request_status",
        ]

    def create(self, validated_data):
        request_files = validated_data.pop('request_files')
        user = self.context['request'].user
        edit_request = EditRequest.objects.create(
            user=user,
            request_type=RequestType.PHOTO_REQUEST,
            **validated_data
        )
        for file in request_files:
            EditRequestGallery.objects.create(
                edit_request=edit_request,
                user_request_file=file,
                file_type=FileTypes.IMAGE,
            )
        return edit_request

class EditRequestListSerializer(serializers.ModelSerializer):
    files = SimpleFileSerializer(many=True, read_only=True, source='request_files')

    class Meta:
        model = EditRequest
        fields = [
            "uid",
            "code",
            "description",
            "special_note",
            "request_status",
            'request_type',
            "desire_delivery_date",
            "files",
            "created_at",
        ]

class EditRequestUpdateStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditRequest
        fields = [
            "request_status",
        ]

    def update(self, instance, validated_data):
        old_status = instance.request_status
        new_status = validated_data['request_status']
        instance.request_status = new_status
        instance.save()

        if old_status != RequestStatus.COMPLETED and new_status == RequestStatus.COMPLETED:
            subject = f"Your {instance.get_request_type_display()} request has been completed!"

            text_content = (
                f"Hello {instance.user.email},\n\n"
                f"Your {instance.get_request_type_display()} request ({instance.code}) has been completed!\n\n"
                f"Please check your account for the completed request.\n\n"
                f"Best regards,\n"
                f"Alibi Team"
            )

            html_content = (
                f"<p>Hello {instance.user.email},</p>"
                f"<p>Your <strong>{instance.get_request_type_display()}</strong> request "
                f"(<strong>{instance.code}</strong>) has been completed!</p>"
                f"<p>Please check your account for the completed request.</p>"
                f"<p>Best regards,<br>Alibi Team</p>"
            )

            send_mail_task.delay(subject, text_content, html_content, instance.user.email)

        return instance

class SouvenirEditRequestGallerySerializer(serializers.ModelSerializer):
    file = serializers.FileField(source="gallery.file", read_only=True)
    file_type = serializers.CharField(source="gallery.file_type", read_only=True)


    class Meta:
        model = EditRequestGallery
        fields = [
            "file",
            "file_type",
            "file_status",
            "quantity",
        ]

class SouvenirEditRequestListSerializer(serializers.ModelSerializer):
    request_files = SouvenirEditRequestGallerySerializer(many=True, read_only=True)

    class Meta:
        model = EditRequest
        fields = [
            "uid",
            "description",
            "special_note",
            "request_status",
            'request_type',
            "desire_delivery_date",
            "created_at",
            "request_files",
        ]


class VideoAudioEditRequestSerializer(serializers.ModelSerializer):
    request_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True
    )
    edit_type = serializers.ChoiceField(
        choices=EditType,
        write_only=True
    )

    class Meta:
        model = EditRequest
        fields = [
            "uid",
            "title",
            "description",
            "special_note",
            "request_status",
            "desire_delivery_date",
            "edit_type",
            "request_files"
        ]
        read_only_fields = [
            "uid",
            "request_status",
        ]
    @transaction.atomic
    def create(self, validated_data):
        request_files = validated_data.pop('request_files')
        edit_type = validated_data.pop('edit_type')

        if edit_type == EditType.VIDEO_EDITING:
            validated_data['request_type'] = RequestType.VIDEO_REQUEST
        elif edit_type == EditType.AUDIO_EDITING:
            validated_data['request_type'] = RequestType.AUDIO_REQUEST

        user = self.context['request'].user
        edit_request = EditRequest.objects.create(
            user=user,
            **validated_data
        )

        # Prepare files data for background processing
        files_data = []
        for file in request_files:
            # Save the file to storage
            filename = f"user-requests/{file.name}"
            path = default_storage.save(filename, file)
            files_data.append({
                'path': path,
                'file_type': FileTypes.VIDEO if edit_type == EditType.VIDEO_EDITING else FileTypes.AUDIO
            })

        # Trigger the background task to process these files
        handle_edit_request_file.delay(edit_request.id, files_data)

        # Process files in background with fallback to synchronous processing
        #     EditRequestGallery.objects.create(
        #             edit_request=edit_request,
        #             user_request_file=file,
        #             file_type=FileTypes.VIDEO,
        #         )

        return edit_request
