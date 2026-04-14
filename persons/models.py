from django.db import models
from django.utils.translation import gettext_lazy as _

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

    class Meta:
        verbose_name = _('Person')
        verbose_name_plural = _('People')

    class Gender(models.IntegerChoices):
        UNKNOWN = 0
        FEMALE = 1
        MALE = 2
        NON_BINARY = 3

    class PersonTranslation(BaseModel):
        """
        Model representing a translation of a person's name and biography.

        Attributes:
            person (models.ForeignKey): The person this translation belongs to.
            language (models.CharField): The language code of the translation.
            biography (models.TextField): The translated biography of the person.
        """

        class Meta:
            verbose_name = _('Person Translation')
            verbose_name_plural = _('Person Translations')
            unique_together = ('person', 'language')

        person = models.ForeignKey(
            'persons.Person', on_delete=models.CASCADE, related_name='translations'
        )
        language = models.CharField(max_length=2)
        biography = models.TextField(blank=True)

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    image = models.ImageField(upload_to='person', default='person/default.png')
    awards = models.ManyToManyField('awards.Award', related_name='persons', blank=True)
    biography = models.TextField(blank=True)
    birthday = models.DateField(null=True, blank=True)
    deathday = models.DateField(null=True, blank=True)
    gender = models.IntegerField(choices=Gender.choices, default=Gender.UNKNOWN)

    def __str__(self):
        return self.slug

    def translate_biography(self, language_code):
        try:
            translation = self.translations.get(language=language_code)
        except self.PersonTranslation.DoesNotExist:
            translation = None
        if translation:
            return translation.biography
        return self.biography
