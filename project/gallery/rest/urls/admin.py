from django.urls import path

from gallery.rest.views.admin import (
    GalleryListCreateView,
    AdminPhotoEditRequestView,
    AdminVideoAudioEditRequestView,
AdminSouvenirRequestView,
AdminPhotoEditRequestRetrieveView,
AdminPhotoEditRequestUpdateStatusView
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
        "/photo-edit-requests/<str:uid>",
        AdminPhotoEditRequestRetrieveView.as_view(),
        name="admin-photo-edit-request-retrieve"
    ),
    # path(
    #     "/photo-edit-requests/<str:uid>/update-status",
    #     AdminPhotoEditRequestUpdateStatusView.as_view(),
    #     name="admin-photo-edit-request-update-status"
    # ),
    path(
        "/video-audio-edit-requests",
        AdminVideoAudioEditRequestView.as_view(),
        name="admin-video-audio-edit-request"
    ),
    path(
        "/souvenir-requests",
        AdminSouvenirRequestView.as_view(),
        name="admin-souvenir-request"
    ),
]
