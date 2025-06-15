from django.contrib import admin
from gallery.models import Gallery, EditRequest, EditRequestGallery


class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'file_type', 'is_public', 'created_by', 'created_at')
    list_filter = ('file_type', 'is_public', 'created_at')
    search_fields = ('title', 'code', 'description', 'created_by__email')
    readonly_fields = ('code', 'created_by', 'updated_by', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class EditRequestGalleryInline(admin.TabularInline):
    model = EditRequestGallery
    extra = 0
    readonly_fields = ('responded_by',)
    autocomplete_fields = ('gallery',)


class EditRequestAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'request_status', 'desire_delivery_date', 'created_at')
    list_filter = ('request_status', 'desire_delivery_date', 'created_at')
    search_fields = ('code', 'description', 'user__email')
    readonly_fields = ('code', 'user', 'created_at', 'updated_at')
    inlines = [EditRequestGalleryInline]
    ordering = ('-created_at',)


class EditRequestGalleryAdmin(admin.ModelAdmin):
    list_display = (
        'edit_request', 'gallery', 'file_status', 'responded_by',
        'admin_response_file', 'individual_note'
    )
    list_filter = ('file_status', 'responded_by')
    search_fields = ('edit_request__code', 'gallery__code', 'individual_note')
    autocomplete_fields = ('edit_request', 'gallery', 'responded_by')
    ordering = ('-edit_request__created_at',)


# Register models using admin.site.register
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(EditRequest, EditRequestAdmin)
admin.site.register(EditRequestGallery, EditRequestGalleryAdmin)
