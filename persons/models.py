from django.db import models

from shared.models import BaseModel


class Person(BaseModel):
    """
    Model representing a celebrity, usually an actor/actress or director.

    Attributes:
        name (models.CharField): The full name of the person.
        slug (models.SlugField): A URL-friendly version of the person's name.
        image (models.ImageField): A profile image of the person.
        country (models.CharField): The country of origin of the person.
    """

    class Country(models.TextChoices):
        """
        Enumeration of supported countries for persons.

        Values:
            SPAIN: Represents Spain.
            ENGLAND: Represents England.
        """

        SPAIN = 'ES', 'Spain'
        ENGLAND = 'EN', 'England'

    name = models.CharField(max_length=32)
    slug = models.SlugField(max_length=32)
    image = models.ImageField(upload_to='person', default='person/default.png')
    country = models.CharField(max_length=4, choices=Country)

    def __str__(self):
        return self.slug