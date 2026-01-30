from django.db import models

from shared.models import Timestamps


class Platform(Timestamps):
    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)
    url = models.URLField(blank=True, null=True)
