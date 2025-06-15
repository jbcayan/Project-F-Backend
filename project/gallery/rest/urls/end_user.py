from django.urls import path

from gallery.rest.views.end_user import (
    EndUserEditRequestView,
    EndUserEditRequestRetrieveView
)

urlpatterns = [
    path(
        "/edit-requests",
        EndUserEditRequestView.as_view(),
        name="end-user-edit-request"
    ),
    path(
        "/edit-request/<str:uid>",
        EndUserEditRequestRetrieveView.as_view(),
        name="end-user-edit-request-retrieve"
    ),
]