from django_filters import rest_framework as filters
from gallery.models import Gallery


class GalleryFilter(filters.FilterSet):
    code = filters.CharFilter(lookup_expr='icontains')
    title = filters.CharFilter(lookup_expr='icontains')
    file_type = filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = Gallery
        fields = ['code', 'title', 'file_type']
