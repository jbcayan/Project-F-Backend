from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permission import (
    CheckAnyPermission,
    IsAdmin,
    IsEndUser,
    IsSuperAdmin,
)
from gallery.choices import FileTypes, RequestType
from gallery.filters import GalleryFilter
from gallery.models import EditRequest, Gallery
from gallery.rest.serializers.end_user import (
    EndUserEditRequestCreateSerializer,
    EndUserEditRequestRetrieveSerializer,
    EditRequestMinimalListSerializer,
    SimpleGallerySerializer,
    PhotoEditRequestSerializer,
    EditRequestListSerializer,
    VideoAudioEditRequestSerializer,
)


@extend_schema(
    summary="Get all edit requests for the end user",
    tags=["End User"]
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
    tags=["End User"]
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
    tags=["End User"]
)
class EndUserGalleyListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser,
    )
    permission_classes = (CheckAnyPermission,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = GalleryFilter
    serializer_class = SimpleGallerySerializer

    def get_queryset(self, *args, **kwargs):
        return Gallery().get_all_actives()


@extend_schema(
    summary="Get all active images from the gallery",
    tags=["End User"]
)
class EndUserGalleyImageListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser,
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = SimpleGallerySerializer

    def get_queryset(self, *args, **kwargs):
        return Gallery().get_all_actives().filter(
            file_type=FileTypes.IMAGE
        )

@extend_schema(
    summary="User can submit a photo request and get a list of all photo requests submitted by the user",
    tags=["End User"]
)
class EndUserPhotoEditRequestView(generics.ListCreateAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser
    )
    permission_classes = (CheckAnyPermission,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PhotoEditRequestSerializer
        return EditRequestListSerializer

    def get_queryset(self, *args, **kwargs):
        try:
            return EditRequest.objects.filter(
                user=self.request.user,
                request_type=RequestType.PHOTO_REQUEST
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found for this user.'
            }, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        serializer = PhotoEditRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Edit request submitted successfully.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="Get a specific photo edit request for the end user",
    tags=["End User"]
)
class EndUserPhotoEditRequestRetrieveView(generics.RetrieveAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser,
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = EditRequestListSerializer

    def get_object(self):
        request_uid = self.kwargs['uid']
        try:
            return EditRequest.objects.get(
                uid=request_uid,
                user=self.request.user,
                request_type=RequestType.PHOTO_REQUEST
            )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found.'
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="User can submit a video or audio request and get a list of all video or audio requests submitted by the user",
    tags=["End User"]
)
class EndUserVideoAudioEditRequestView(generics.ListCreateAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser
    )
    permission_classes = (CheckAnyPermission,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VideoAudioEditRequestSerializer
        return EditRequestListSerializer

    def get_queryset(self, *args, **kwargs):
        try:
            return EditRequest.objects.filter(
                user=self.request.user
                ).filter(
                    Q(request_type=RequestType.VIDEO_REQUEST) |
                    Q(request_type=RequestType.AUDIO_REQUEST)
                )
        except EditRequest.DoesNotExist:
            return Response({
                'message': 'No edit requests found for this user.'
            }, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        serializer = VideoAudioEditRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Edit request submitted successfully.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
