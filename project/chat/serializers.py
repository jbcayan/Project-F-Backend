from rest_framework import serializers
from chat.models import ChatThread, ChatMessage
from accounts.models import User


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    sender_kind = serializers.CharField(source='sender.kind', read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'thread',
            'sender',
            'sender_email',
            'sender_kind',
            'text',
            'created_at',
            'is_read',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'sender_email',
            'sender_kind',
            'sender',
        ]

    def create(self, validated_data):
        """
        Automatically set the sender to the logged-in user.
        """
        user = self.context['request'].user
        validated_data['sender'] = user
        return super().create(validated_data)


class ChatThreadSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatThread
        fields = [
            'id',
            'user',
            'user_email',
            'created_at',
            'messages',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'user',
            'user_email',
            'messages',
        ]

    def create(self, validated_data):
        """
        Automatically set the thread initiator to the logged-in user.
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)
