from django.db import models

from shared.models import Timestamps


class Person(Timestamps):
    """
    Model representing a celebrity, usually an actor/actress or director.

    Attributes:
        name (CharField): The full name of the person.
        slug (SlugField): A URL-friendly version of the person's name.
        image (ImageField): A profile image of the person.
        country (CharField): The country of origin of the person.
    """
    class Country(models.TextChoices):
        """
        Enumeration of supported countries for persons.
        """
        SPAIN = 'ES', 'Spain'
        ENGLAND = 'EN', 'England'

    name = models.CharField(max_length=32)
    slug = models.SlugField(max_length=32)
    image = models.ImageField(upload_to='person', default='person/default.png')
    country = models.CharField(max_length=4, choices=Country)
