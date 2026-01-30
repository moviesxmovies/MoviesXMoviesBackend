from django.db import models

from shared.models import Timestamps

class Genre(Timestamps):
    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)
