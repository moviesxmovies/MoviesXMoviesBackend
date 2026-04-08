from django.db import models

from shared.models import BaseModel
from django.utils.translation import gettext_lazy as _


class Platform(BaseModel):
    """
    Model representing a streaming platform.

    Attributes:
        name (models.CharField): The name of the platform.
        slug (models.SlugField): A URL-friendly version of the platform's name.
        url (models.URLField): The official website URL of the platform.
    """

    class Meta:
        verbose_name = _('Platform')
        verbose_name_plural = _('Platforms')

    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)
    url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='platforms/', blank=True, null=True)

    def __str__(self):
        return self.slug
