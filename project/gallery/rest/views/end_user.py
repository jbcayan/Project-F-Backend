from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics

from common.permission import (
    CheckAnyPermission,
    IsAdmin,
    IsEndUser,
    IsSuperAdmin,
)
from gallery.choices import FileTypes
from gallery.filters import GalleryFilter
from gallery.models import EditRequest, Gallery
from gallery.rest.serializers.end_user import (
    EndUserEditRequestCreateSerializer,
    EndUserEditRequestRetrieveSerializer,
    EditRequestMinimalListSerializer, SimpleGallerySerializer
)


@extend_schema(
    summary="Get all edit requests for the end user",
    tags=["END USER"]
)
class EndUserEditRequestView(generics.ListCreateAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser,
    )
    permission_classes = (CheckAnyPermission,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EndUserEditRequestCreateSerializer
        return EditRequestMinimalListSerializer

    def get_queryset(self, *args, **kwargs):
        return EditRequest.objects.filter(
            user=self.request.user
        )

@extend_schema(
    summary="Get a specific edit request for the end user",
    tags=["END USER"]
)
class EndUserEditRequestRetrieveView(generics.RetrieveAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EndUserEditRequestRetrieveSerializer
    lookup_field = 'uid'


    def get_queryset(self, *args, **kwargs):
        return EditRequest.objects.filter(
            # uid=self.kwargs['uid'],
            user=self.request.user
        )

@extend_schema(
    summary="Get all active items from the gallery, Filter included",
    tags=["END USER"]
)
class EndUserGalleyListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser
    )
    permission_classes = (CheckAnyPermission,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = GalleryFilter
    serializer_class = SimpleGallerySerializer

    def get_queryset(self, *args, **kwargs):
        return Gallery().get_all_actives()


@extend_schema(
    summary="Get all active images from the gallery",
    tags=["END USER"]
)
class EndUserGalleyImageListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = SimpleGallerySerializer

    def get_queryset(self, *args, **kwargs):
        return Gallery().get_all_actives().filter(
            file_type=FileTypes.IMAGE
        )