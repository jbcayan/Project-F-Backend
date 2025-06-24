from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chat.views import ChatThreadViewSet, ChatMessageViewSet

# DRF router for automatic ViewSet routing
router = DefaultRouter()
router.register(r'threads', ChatThreadViewSet, basename='chat-thread')
router.register(r'messages', ChatMessageViewSet, basename='chat-message')

urlpatterns = [
    path('', include(router.urls)),  # Includes /threads/, /messages/, etc.
]
