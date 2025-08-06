from rest_framework import serializers

from chat.models import ChatThread, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    sender_kind = serializers.CharField(source='sender.kind', read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'thread',
            # 'sender',
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
    unread_messages_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatThread
        fields = [
            'id',
            # 'user',
            'user_email',
            'created_at',
            'messages',
            "unread_messages_count",
        ]
        read_only_fields = [
            'id',
            'created_at',
            # 'user',
            'user_email',
            'messages',
        ]

    def get_unread_messages_count(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return 0
        user = request.user
        if hasattr(user, 'kind'):
            if user.kind in ['ADMIN', 'SUPER_ADMIN']:
                return obj.messages.filter(is_read=False, sender__kind='END_USER').count()
            else:
                return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0

    def create(self, validated_data):
        """
        Automatically set the thread initiator to the logged-in user.
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)
