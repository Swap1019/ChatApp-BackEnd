from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField
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
    class Meta:
        model = Conversation
        fields = "__all__"
        read_only_fields = [
            "id",
        ]
