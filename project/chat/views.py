from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from chat.models import ChatThread, ChatMessage
from chat.serializers import ChatThreadSerializer, ChatMessageSerializer


class IsAdminOrOwner(permissions.BasePermission):
    """
    Allow users to access their own threads, and admins to access all.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.kind in ['ADMIN', 'SUPER_ADMIN']:
            return True
        return obj.user == request.user


class ChatThreadViewSet(viewsets.ModelViewSet):
    """
    Viewset for chat threads.
    Users see only their own; admins see all.
    """
    serializer_class = ChatThreadSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.kind in ['ADMIN', 'SUPER_ADMIN']:
            return ChatThread.objects.all()
        return ChatThread.objects.filter(user=user)

    @action(detail=True, methods=['post'], url_path='mark_all_read')
    def mark_all_read(self, request, pk=None):
        """
        Mark all unread messages in a thread as read, based on role.
        - Users mark admin messages as read
        - Admins mark user messages as read
        """
        thread = self.get_object()
        user = request.user
        user_kind = user.kind

        if user_kind in ['ADMIN', 'SUPER_ADMIN']:
            unread_messages = thread.messages.filter(is_read=False, sender__kind='END_USER')
        else:
            unread_messages = thread.messages.filter(is_read=False).exclude(sender=user)

        count = unread_messages.update(is_read=True)

        return Response(
            {"detail": f"{count} message(s) marked as read."},
            status=status.HTTP_200_OK
        )


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    Viewset for chat messages.
    Users and admins can view messages in threads they have access to.
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        thread_id = self.request.query_params.get('thread')

        queryset = ChatMessage.objects.all()

        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)

        if user.kind in ['ADMIN', 'SUPER_ADMIN']:
            return queryset
        return queryset.filter(thread__user=user)

    def perform_create(self, serializer):
        serializer.save()
