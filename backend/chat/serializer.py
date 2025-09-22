from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from user.serializers import UserSerializer
from .models import (
    Conversation,
    Message,
)


class MessageSerializer(ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = "__all__"


class ConversationSerializer(ModelSerializer):
    profile = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = Conversation
        fields = "__all__"
        read_only_fields = [
            "id",
        ]
