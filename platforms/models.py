from django.db import models

from shared.models import BaseModel


class Platform(BaseModel):
    """
    Model representing a streaming platform.

    Attributes:
        name (models.CharField): The name of the platform.
        slug (models.SlugField): A URL-friendly version of the platform's name.
        url (models.URLField): The official website URL of the platform.
    """

    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)
    url = models.URLField(blank=True, null=True)
