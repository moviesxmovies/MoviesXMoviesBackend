from django.db import models

from shared.models import Timestamps


class Person(Timestamps):
    class Country(models.TextChoices):
        SPAIN = 'ES', 'Spain'
        ENGLAND = 'EN', 'England'

    name = models.CharField(max_length=32)
    slug = models.SlugField(max_length=32)
    image = models.ImageField(upload_to='person', default='person/default.png')
    country = models.CharField(max_length=4, choices=Country)
