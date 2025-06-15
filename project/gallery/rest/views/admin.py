from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics

from common.permission import IsAdmin, IsSuperAdmin, CheckAnyPermission
from gallery.filters import GalleryFilter
from gallery.models import Gallery
from gallery.rest.serializers.admin import GalleryUploadSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Gallery list and create for Admin Users only",
    request=GalleryUploadSerializer,
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
