from django.contrib import admin
from chat.models import ChatThread, ChatMessage


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    """
    Admin view for ChatThread
    """
    list_display = ('id', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    Admin view for ChatMessage
    """
    list_display = (
        'id', 'thread', 'sender', 'short_text', 'is_read', 'created_at'
    )
    list_filter = (
        'is_read', 'created_at', 'sender__kind'
    )
    search_fields = (
        'text', 'sender__email', 'thread__user__email'
    )
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def short_text(self, obj):
        """
        Show a truncated version of the message text in the list view.
        """
        if not obj.text:
            return "(Empty)"
        return obj.text[:50] + ('...' if len(obj.text) > 50 else '')
    short_text.short_description = 'Message'
