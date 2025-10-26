from django.db import models
from user.models import User
from cloudinary.models import CloudinaryField
from cloudinary import CloudinaryImage
import uuid


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, verbose_name="Conversation name", default="Private")
    members = models.ManyToManyField(User, verbose_name="Members", related_name="chats")
    is_group = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Group creation date")
    profile = CloudinaryField("image",null=True,blank=True)

    def __str__(self):
        return self.name
    
    @property
    def profile_url(self):
        if not self.profile:
            return None
        return CloudinaryImage(self.profile.public_id).build_url(
            fetch_format="webp"
        )
    


class Message(models.Model):
    conversation = models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name="messages")
    sender = models.ForeignKey(User,verbose_name="Sender",on_delete=models.SET_NULL,null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="Sent at")
    is_read = models.BooleanField(default=False,verbose_name="Seen status")

    class Meta:
        ordering = ['created_at']

class Contact(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owner")
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contact")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'contact')

