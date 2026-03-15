from django.db import models

from shared.models import BaseModel
from django.utils.translation import gettext_lazy as _


class Person(BaseModel):
    """
    Model representing a celebrity, usually an actor/actress or director.

    Attributes:
        name (models.CharField): The full name of the person.
        slug (models.SlugField): A URL-friendly version of the person's name.
        image (models.ImageField): A profile image of the person.
        country (models.CharField): The country of origin of the person.
    """
    class Meta:
        verbose_name = _('Person')
        verbose_name_plural = _('People')

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    image = models.ImageField(upload_to='person', default='person/default.png')
    awards = models.ManyToManyField('awards.Award', related_name='persons', blank=True)

    def __str__(self):
        return self.slug
