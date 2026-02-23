from rest_framework import serializers
from user.serializers import (
    UserMessageSerializer,
)

from .models import (
    Conversation,
    Message,
    MessagesMedia,
    Contact,
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
        fields = ("id", "message", "name", "file", "url", "kind")


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMessageSerializer(read_only=True)
    media_files = MessageMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = "__all__"


class ConversationSerializer(serializers.ModelSerializer):
    profile = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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


class ContactSerializer(serializers.ModelSerializer):
    contact = UserMessageSerializer(read_only=True)

    class Meta:
        model = Contact
        fields = ("id", "contact", "created_at")


class AddContactSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()


class GroupConversationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=50
    )
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )


class GroupMembersAddSerializer(serializers.Serializer):
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        allow_empty=False,
    )
