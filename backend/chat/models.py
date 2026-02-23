from django.db import models
from user.models import User
import uuid


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50, verbose_name="Conversation name", default="Private"
    )
    members = models.ManyToManyField(User, verbose_name="Members", related_name="chats")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_conversations",
    )
    admins = models.ManyToManyField(
        User,
        blank=True,
        related_name="admin_conversations",
    )
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Group creation date"
    )
    profile = models.TextField(null=True, blank=True, verbose_name="chat")

    def __str__(self):
        return self.name

    @property
    def profile_url(self):
        if not self.profile:
            return None
        return str(self.profile)

    def get_other_member(self, user):
        # Returns the other user in a private conversation.
        members = self.members.exclude(id=user.id).only(
            "id","username","nickname","bio","profile"
        )
        if not members.exists():
            raise ValueError("User is not part of this conversation")

        return members.first()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, verbose_name="Sender", on_delete=models.SET_NULL, null=True
    )
    content = models.TextField()
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sent at")
    is_read = models.BooleanField(default=False, verbose_name="Seen status")

    class Meta:
        ordering = ["created_at"]


class Contact(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owner")
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contact")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner", "contact")


class MessagesMedia(models.Model):
    KIND_CHOICES = (
        ("image", "image"),
        ("video", "video"),
        ("file", "file"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="media_files",
        verbose_name="Message",
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to="messages_media/")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, null=True, blank=True)
