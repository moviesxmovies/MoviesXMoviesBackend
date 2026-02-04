from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.

    Attributes:
        bio (models.TextField): A brief biography of the user.
    """
    bio = models.TextField(blank=True, null=True)
    boarded = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)