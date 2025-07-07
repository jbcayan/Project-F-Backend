import csv
import io
import os
import requests
import zipfile
from datetime import datetime
from urllib.request import urlopen

from django.db.models import Q
from django.http import FileResponse
from django.utils.timezone import make_aware
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from common.permission import IsAdmin, IsSuperAdmin, CheckAnyPermission
from gallery.choices import RequestType
from gallery.filters import GalleryFilter
from gallery.models import Gallery, EditRequest
from gallery.rest.serializers.admin import (
    GalleryDetailSerializer,
    GalleryUploadSerializer,
    DownloadRequestSerializer,
    GalleryDetailSerializer
)
from gallery.rest.serializers.end_user import (
    EditRequestListSerializer,
    SouvenirEditRequestListSerializer,
    EditRequestUpdateStatusSerializer
)


@extend_schema(
    summary="Gallery list and create for Admin Users only",
    request=GalleryUploadSerializer,
    tags=["Admin"],
)
class GalleryListCreateView(generics.ListCreateAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = GalleryFilter
    serializer_class = GalleryUploadSerializer
    queryset = Gallery.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user, updated_by=user)

@extend_schema(
    summary="Gallery detail, update and delete for Admin Users only",
    tags=["Admin"],
)
class GalleryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = GalleryDetailSerializer
    queryset = Gallery.objects.all()

    def get_object(self):
        uid = self.kwargs.get('uid')
        try:
            return Gallery.objects.get(uid=uid)
        except Gallery.DoesNotExist:
            raise NotFound

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(updated_by=user)


    def perform_destroy(self, instance):
        instance.delete()


@extend_schema(
    summary="Photo edit request list for Admin Users only",
    tags=["Admin"],
)
class AdminPhotoEditRequestView(generics.ListAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestListSerializer

    def get_queryset(self, *args, **kwargs):
        try:
            return EditRequest.objects.filter(
                request_type=RequestType.PHOTO_REQUEST
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found.'
            }, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    summary="Photo edit request retrieve for Admin Users only",
    tags=["Admin"],
)
class AdminPhotoEditRequestRetrieveView(generics.RetrieveAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestListSerializer

    def get_object(self):
        request_uid = self.kwargs['uid']
        try:
            return EditRequest.objects.get(
                uid=request_uid,
                request_type=RequestType.PHOTO_REQUEST
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found.'
            }, status=status.HTTP_404_NOT_FOUND)



@extend_schema(
    summary="Photo edit request update status for Admin Users only",
    tags=["Admin"],
)
class AdminPhotoEditRequestUpdateStatusView(generics.UpdateAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestUpdateStatusSerializer
    http_method_names = ['patch']

    def get_object(self):
        uid = self.kwargs.get('uid')
        try:
            obj = EditRequest.objects.get(
                uid=uid,
                request_type=RequestType.PHOTO_REQUEST
            )
            return obj
        except EditRequest.DoesNotExist:
            raise NotFound(detail="Photo edit request not found")

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        response.data['message'] = "Photo edit request status updated successfully"
        return response


@extend_schema(
    summary="Video and Audio edit request list for Admin Users only",
    tags=["Admin"],
)
class AdminVideoAudioEditRequestView(generics.ListAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestListSerializer

    def get_queryset(self, *args, **kwargs):
        try:
            return EditRequest.objects.filter(
                Q(request_type=RequestType.VIDEO_REQUEST) |
                Q(request_type=RequestType.AUDIO_REQUEST)
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found.'
            }, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    summary="Video and Audio edit request retrieve for Admin Users only",
    tags=["Admin"],
)
class AdminVideoAudioEditRequestRetrieveView(generics.RetrieveAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestListSerializer

    def get_object(self):
        request_uid = self.kwargs['uid']
        try:
            return EditRequest.objects.get(
                Q(uid=request_uid) & (
                        Q(request_type=RequestType.VIDEO_REQUEST) |
                        Q(request_type=RequestType.AUDIO_REQUEST)
                )
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found.'
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Video and Audio edit request update status for Admin Users only",
    tags=["Admin"],
)
class AdminVideoAudioEditRequestUpdateStatusView(generics.UpdateAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestUpdateStatusSerializer
    http_method_names = ['patch']

    def get_object(self):
        request_uid = self.kwargs.get('uid')
        try:
            obj = EditRequest.objects.get(
                Q(uid=request_uid) & (
                        Q(request_type=RequestType.VIDEO_REQUEST) |
                        Q(request_type=RequestType.AUDIO_REQUEST)
                )
            )
            return obj
        except EditRequest.DoesNotExist:
            raise NotFound(detail="Video and Audio edit request not found")

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        response.data['message'] = "Video and Audio edit request status updated successfully"
        return response


@extend_schema(
    summary="Souvenir edit request list for Admin Users only",
    tags=["Admin"],
)
class AdminSouvenirRequestView(generics.ListAPIView):
    available_permission_classes = (
        IsAdmin,
        IsSuperAdmin
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = SouvenirEditRequestListSerializer

    def get_queryset(self, *args, **kwargs):
        try:
            return EditRequest.objects.filter(
                request_type=RequestType.SOUVENIR_REQUEST
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found.'
            }, status=status.HTTP_404_NOT_FOUND)


import concurrent.futures

@extend_schema(
    summary="Download edit requests for Admin Users only",
    tags=["Admin"],
    parameters=[
        OpenApiParameter(
            name='start_date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description='Start date for filtering requests (YYYY-MM-DD)'
        ),
        OpenApiParameter(
            name='end_date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description='End date for filtering requests (YYYY-MM-DD)'
        ),
        OpenApiParameter(
            name='request_type',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Filter by specific request type',
            enum=[choice[0] for choice in RequestType.choices]  # Show all available choices
        ),
    ],
    responses={
        200: OpenApiResponse(description='Zip file containing all edit requests'),
        400: OpenApiResponse(description='Invalid input data'),
        403: OpenApiResponse(description='Permission denied')
    }
)
class EditRequestDownloadView(generics.GenericAPIView):
    available_permission_classes = (IsAdmin, IsSuperAdmin)
    permission_classes = (CheckAnyPermission,)

    def get(self, request):
        serializer = DownloadRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start_date = make_aware(datetime.combine(serializer.validated_data['start_date'], datetime.min.time()))
        end_date = make_aware(datetime.combine(serializer.validated_data['end_date'], datetime.max.time()))
        request_type = serializer.validated_data.get('request_type')

        requests_items = EditRequest.objects.filter(
            created_at__range=(start_date, end_date),
            request_type=request_type if request_type else None
        ).prefetch_related('request_files__gallery')

        if not requests_items.exists():
            return Response({'message': 'No edit requests found.'}, status=status.HTTP_404_NOT_FOUND)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for req in requests_items:
                folder_name = f"{req.uid}/"
                files = req.request_files.all()

                # CSV data
                csv_buffer = io.StringIO()
                csv_writer = csv.writer(csv_buffer)
                csv_writer.writerow([
                    'title', 'special_note', 'description', 'request_status', 'desire_delivery_date',
                    'request_type', 'shipping_address', 'additional_notes', 'file_urls'
                ])
                file_urls = ';'.join([f.user_request_file.url for f in files if f.user_request_file])
                csv_writer.writerow([
                    req.title, req.special_note, req.description, req.request_status,
                    req.desire_delivery_date, req.request_type, req.shipping_address,
                    req.additional_notes, file_urls
                ])
                zip_file.writestr(folder_name + 'data.csv', csv_buffer.getvalue())

                # Download files in parallel
                def download_file(f):
                    if f.user_request_file and f.user_request_file.url:
                        try:
                            response = requests.get(f.user_request_file.url, timeout=10)
                            response.raise_for_status()
                            filename = os.path.basename(f.user_request_file.name)
                            return (filename, response.content)
                        except Exception as e:
                            print(f"Error downloading {f.user_request_file.url}: {str(e)}")
                    return None

                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    future_to_file = {executor.submit(download_file, f): f for f in files}
                    for future in concurrent.futures.as_completed(future_to_file):
                        result = future.result()
                        if result:
                            filename, content = result
                            zip_file.writestr(folder_name + filename, content)

        zip_buffer.seek(0)
        filename = f"{serializer.validated_data['start_date']}_to_{serializer.validated_data['end_date']}.zip"
        response = FileResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response