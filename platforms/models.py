from django.db import models

class Platform(models.Model):
    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)
    url = models.URLField(blank=True, null=True)