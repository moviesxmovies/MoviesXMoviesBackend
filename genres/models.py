from django.db import models

from shared.models import BaseModel
from django.utils.translation import gettext_lazy as _


class Genre(BaseModel):
    """
    A movie genre model

    Attributes:
        name (models.CharField): The name of the genre.
        slug (models.SlugField): A URL-friendly version of the genre's name.
    """
    class Meta:
        verbose_name = _('Genre')
        verbose_name_plural = _('Genres')

    class GenreTranslation(BaseModel):
        """
        A model representing the translation of a genre's name.

        Attributes:
            genre (models.ForeignKey): A foreign key to the Genre model.
            language (models.CharField): The language code for the translation.
            name (models.CharField): The translated name of the genre.
        """

        class Meta:
            unique_together = ('genre', 'language')
            verbose_name = _('Genre Translation')
            verbose_name_plural = _('Genre Translations')

        genre = models.ForeignKey('Genre', related_name='translations', on_delete=models.CASCADE)
        language = models.CharField(max_length=2)
        name = models.CharField(max_length=32)
        def __str__(self):
            return f'{self.genre.name} ({self.language})'

    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)

    def __str__(self):
        return self.slug

    def translate_name(self, language):
        try:
            translation = self.translations.get(language=language)
        except self.GenreTranslation.DoesNotExist:
            translation = None
        if translation:
            return translation.name
        return self.name
