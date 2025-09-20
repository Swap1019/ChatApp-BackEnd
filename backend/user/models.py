from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nickname = models.CharField(max_length=30,verbose_name="Nick Name",blank=True,null=True)
    profile = CloudinaryField("profile",blank=True, null=True)
    background_image = CloudinaryField("background_image",blank=True,null=True)
    bio = models.CharField(max_length=80, verbose_name="Bio", blank=True, null=True)
    email = models.EmailField(unique=True,verbose_name="Email")

    def __str__(self):
        return self.username
