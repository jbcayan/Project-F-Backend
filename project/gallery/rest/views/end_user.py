from rest_framework import status
from rest_framework.response import Response
from rest_framework import generics
from common.permission import (
    CheckAnyPermission,
    IsAdmin,
    IsEndUser,
    IsSuperAdmin,
)
from gallery.rest.serializers.end_user import (
    EndUserEditRequestCreateSerializer,
    EndUserEditRequestRetrieveSerializer,
    EditRequestMinimalListSerializer, SimpleGallerySerializer
)
from gallery.models import EditRequest, Gallery


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


class EndUserGalleyListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = SimpleGallerySerializer

    def get_queryset(self, *args, **kwargs):
        gallery = Gallery().get_all_actives()
        return gallery