from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField
from rest_framework import serializers
from user.serializers import (
    UserSerializer,
    UserSettingsSerializer,
    UserMessageSerializer,
)

from .models import (
    Conversation,
    Message,
)


class MessageSerializer(ModelSerializer):
    sender = UserMessageSerializer(read_only=True)

    class Meta:
        model = Message
        fields = "__all__"


class ConversationSerializer(ModelSerializer):
    profile = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = Conversation
        exclude = ["created_at","members"]
        read_only_fields = [
            "id",
        ]
