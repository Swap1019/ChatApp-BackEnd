from django.db import models
from user.models import User
import uuid


class Conversations(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, verbose_name="Conversation name", default="Private")
    members = models.ManyToManyField(User, verbose_name="Members", related_name="users")
    is_group = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Group creation date")


class Messages(models.Model):
    conversation = models.ForeignKey(Conversations,on_delete=models.CASCADE)
    sender = models.ForeignKey(User,verbose_name="Sender",on_delete=models.SET_NULL,null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="Sent at")
    is_read = models.BooleanField(default=False,verbose_name="Seen status")

class Contacts(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owner")
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contact")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'contact')

