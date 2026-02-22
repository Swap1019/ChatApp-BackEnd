from rest_framework import serializers
from user.serializers import (
    UserMessageSerializer,
)

from .models import (
    Conversation,
    Message,
    MessagesMedia,
)


class MessageMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    kind = serializers.SerializerMethodField()

    def get_url(self, obj):
        file_name = str(obj.file)
        if file_name.startswith("http://") or file_name.startswith("https://"):
            return file_name
        try:
            return obj.file.url
        except Exception:
            return file_name

    def get_kind(self, obj):
        if obj.kind:
            return obj.kind
        file_name = (str(obj.file) or "").lower()
        if any(file_name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]):
            return "image"
        if any(file_name.endswith(ext) for ext in [".mp4", ".webm", ".ogg", ".mov", ".mkv", ".m4v"]):
            return "video"
        return None

    class Meta:
        model = MessagesMedia
        fields = ("id", "message", "file", "url", "kind")


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMessageSerializer(read_only=True)
    media_files = MessageMediaSerializer(many=True, read_only=True)

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
