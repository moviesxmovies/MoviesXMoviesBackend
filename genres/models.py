from django.db import models

from shared.models import BaseModel


class Genre(BaseModel):
    """
    A movie genre model

    Attributes:
        name (models.CharField): The name of the genre.
        slug (models.SlugField): A URL-friendly version of the genre's name.
    """

    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)

    def __str__(self):
        return self.slug