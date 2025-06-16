from django.urls import path

from gallery.rest.views.end_user import (
    EndUserEditRequestView,
    EndUserEditRequestRetrieveView,
    EndUserGalleyListView,
    EndUserGalleyImageListView,

)

urlpatterns = [
    path(
        "/edit-requests",
        EndUserEditRequestView.as_view(),
        name="end-user-edit-request"
    ),
    path(
        "/edit-requests/<str:uid>",
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
]