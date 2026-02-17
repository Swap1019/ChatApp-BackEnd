from rest_framework import serializers
from user.serializers import (
    UserMessageSerializer,
)

from .models import (
    Conversation,
    Message,
)


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMessageSerializer(read_only=True)

    class Meta:
        model = Message
        fields = "__all__"


class ConversationSerializer(serializers.ModelSerializer):
    profile = serializers.ImageField(use_url=True, required=False)
    profile_url = serializers.ReadOnlyField()

    class Meta:
        model = Conversation
        exclude = ["created_at","members"]
        read_only_fields = [
            "id",
            "profile_url",
        ]

class MemberSearchSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    nickname = serializers.CharField(allow_null=True)
    profile_url = serializers.ReadOnlyField(allow_null=True)
