from django.urls import path

from gallery.rest.views.admin import (
    GalleryListCreateView,
    AdminPhotoEditRequestView,
    AdminVideoAudioEditRequestView
)

urlpatterns = [
    path(
        "",
        GalleryListCreateView.as_view(),
        name="gallery-list-create"
    ),
    path(
        "/photo-edit-requests",
        AdminPhotoEditRequestView.as_view(),
        name="admin-photo-edit-request"
    ),
    path(
        "/video-audio-edit-requests",
        AdminVideoAudioEditRequestView.as_view(),
        name="admin-video-audio-edit-request"
    ),
]
