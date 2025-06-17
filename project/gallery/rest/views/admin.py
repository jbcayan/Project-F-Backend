from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.response import Response

from common.permission import IsAdmin, IsSuperAdmin, CheckAnyPermission
from gallery.choices import RequestType
from gallery.filters import GalleryFilter
from gallery.models import Gallery, EditRequest
from gallery.rest.serializers.admin import GalleryUploadSerializer
from drf_spectacular.utils import extend_schema

from gallery.rest.serializers.end_user import EditRequestListSerializer


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

