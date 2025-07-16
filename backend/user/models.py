from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ImageField(verbose_name="Profile Picture", blank=True, null=True)
    bio = models.CharField(max_length=350, verbose_name="Bio", blank=True, null=True)
    email = models.EmailField(unique=True,verbose_name="Email")
