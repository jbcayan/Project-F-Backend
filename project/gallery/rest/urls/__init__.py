from django.urls import path, include

from .end_user import urlpatterns as end_user_urls
from .admin import urlpatterns as admin_urls

urlpatterns = [
    path("", include(end_user_urls)),
    path("/admin", include(admin_urls)),
]