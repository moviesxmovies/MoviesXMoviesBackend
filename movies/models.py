from django.db import models
from django.utils.translation import gettext_lazy as _

from shared.models import BaseModel


class Movie(BaseModel):
    """
    A model representing a movie with its details.

    Attributes:
        title (models.CharField): The title of the movie.
        slug (models.SlugField): A URL-friendly version of the movie's title.
        synopsis (models.TextField): A brief summary of the movie's plot.
        release_date (models.DateField): The date when the movie was released.
        cover (models.ImageField): An image representing the movie's cover.
        directors (models.ManyToManyField): A many-to-many relationship to the Person model for directors.
        actors (models.ManyToManyField): A many-to-many relationship to the Person model for actors.
        genres (models.ManyToManyField): A many-to-many relationship to the Genre model.
        platforms (models.ManyToManyField): A many-to-many relationship to the Platform model
    """

    class Meta:
        verbose_name = _('Movie')
        verbose_name_plural = _('Movies')

    class MovieTranslation(BaseModel):
        """
        A model representing the translation of a movie's title and synopsis.

        Attributes:
            movie (models.ForeignKey): A foreign key to the Movie model.
            language (models.CharField): The language code for the translation.
            title (models.CharField): The translated title of the movie.
            synopsis (models.TextField): The translated synopsis of the movie.
        """

        class Meta:
            unique_together = ('movie', 'language')
            verbose_name = _('Movie Translation')
            verbose_name_plural = _('Movie Translations')

        movie = models.ForeignKey('Movie', related_name='translations', on_delete=models.CASCADE)
        language = models.CharField(max_length=2)
        title = models.CharField(max_length=255)
        synopsis = models.TextField()
        image = models.ImageField(upload_to='movies/translations/covers', null=True, blank=True)

        def __str__(self):
            return f'{self.movie.title} ({self.language})'

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    synopsis = models.TextField()
    release_date = models.DateField(db_index=True)
    cover = models.ImageField(upload_to='movies/covers', default='movies/covers/no-movie.png')
    directors = models.ManyToManyField('persons.Person', related_name='directed_movies')
    actors = models.ManyToManyField('persons.Person', related_name='acted_movies')
    genres = models.ManyToManyField('genres.Genre', related_name='movies')
    platforms = models.ManyToManyField('platforms.Platform', related_name='movies', blank=True)
    awards = models.ManyToManyField('awards.Award', related_name='movies', blank=True)

    def __str__(self):
        return self.slug

    def _get_prefetched_translation(self, language):
        if hasattr(self, 'prefetched_translations'):
            for t in self.prefetched_translations:
                if t.language == language:
                    return t
            return None

        return self.translations.filter(language=language).first()

    def translate_title(self, language):
        translation = self._get_prefetched_translation(language)
        return translation.title if translation else self.title

    def translate_synopsis(self, language):
        translation = self._get_prefetched_translation(language)
        return translation.synopsis if translation else self.synopsis

    def translate_image(self, language):
        translation = self._get_prefetched_translation(language)
        if translation and translation.image:
            return translation.image.url
        return self.cover.url
