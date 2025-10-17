from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from cloudinary import CloudinaryImage
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
    
    @property
    def profile_url(self):
        if not self.profile:
            return None
        return CloudinaryImage(self.profile.public_id).build_url(
            fetch_format="webp"
        )
    
    @property
    def background_image_url(self):
        if not self.background_image:
            return None
        return CloudinaryImage(self.background_image.public_id).build_url(
            fetch_format="webp"
        )
