from django.urls import path
from gallery.rest.views.admin import (
    GalleryListCreateView,
)



urlpatterns = [
    path(
        "",
        GalleryListCreateView.as_view(),
        name="gallery-list-create"
    ),
]