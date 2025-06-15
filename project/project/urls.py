from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

admin.site.site_header = "Project F Admin"
admin.site.site_title = "Project F Admin Panel"
admin.site.index_title = "Welcome to Project F Panel"

from .health_check import HealthCheckView

urlpatterns = [
    path('', HealthCheckView.as_view(), name='health_check'),
    path('admin/', admin.site.urls),
    path('users', include('accounts.rest.urls.user')),
    path('gallery', include('gallery.rest.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
