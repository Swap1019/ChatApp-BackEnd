from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nickname = models.CharField(max_length=30,verbose_name="Nick Name",blank=True,null=True)
    profile = models.TextField(blank=True, null=True, verbose_name="profile")
    background_image = models.TextField(blank=True, null=True, verbose_name="background_image")
    bio = models.CharField(max_length=80, verbose_name="Bio", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    phone_number = PhoneNumberField(
        max_length=20,
        verbose_name="Phone Number",
        blank=True,
        null=True,
        unique=True,
    )

    def __str__(self):
        return self.username
    
    @property
    def profile_url(self):
        if not self.profile:
            return None
        return str(self.profile)
    
    @property
    def background_image_url(self):
        if not self.background_image:
            return None
        return str(self.background_image)
