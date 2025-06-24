from django.db import models
from django.conf import settings


class ChatThread(models.Model):
    """
    A chat thread initiated by a user.
    Admins can view and respond to all threads.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_threads'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Thread with {self.user.email}"


class ChatMessage(models.Model):
    """
    A message within a chat thread.
    Can be sent by either a user or an admin.
    """
    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.email}"
