from django.urls import path

from gallery.rest.views.end_user import (
    EndUserEditRequestView,
    EndUserEditRequestRetrieveView,
    EndUserGalleyListView,
    EndUserGalleyImageListView,
    EndUserPhotoEditRequestView,
    EndUserVideoAudioEditRequestView,
    EndUserPhotoEditRequestRetrieveView,
    EndUserVideoAudioEditRequestRetrieveView
)

urlpatterns = [
    path(
        "/souvenir-requests",
        EndUserEditRequestView.as_view(),
        name="end-user-edit-request"
    ),
    path(
        "/souvenir-requests/<str:uid>",
        EndUserEditRequestRetrieveView.as_view(),
        name="end-user-edit-request-retrieve"
    ),
    path(
        "",
        EndUserGalleyListView.as_view(),
        name="end-user-gallery-list"
    ),
    path(
        "/images",
        EndUserGalleyImageListView.as_view(),
        name="end-user-gallery-image-list"
    ),
    path(
        "/photo-edit-requests",
        EndUserPhotoEditRequestView.as_view(),
        name="end-user-photo-edit-request"
    ),
    path(
        "/photo-edit-requests/<str:uid>",
        EndUserPhotoEditRequestRetrieveView.as_view(),
        name="end-user-photo-edit-request-retrieve"
    ),
    path(
        "/video-audio-edit-requests",
        EndUserVideoAudioEditRequestView.as_view(),
        name="end-user-video-audio-edit-request"
    ),
    path(
        "/video-audio-edit-requests/<str:uid>",
        EndUserVideoAudioEditRequestRetrieveView.as_view(),
        name="end-user-video-audio-edit-request-retrieve"
    ),
]