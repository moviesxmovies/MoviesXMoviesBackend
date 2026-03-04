from django.db import models

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

    class MovieTranslation(models.Model):
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

        movie = models.ForeignKey('Movie', related_name='translations', on_delete=models.CASCADE)
        language = models.CharField(max_length=2)
        title = models.CharField(max_length=100)
        synopsis = models.TextField()
        image = models.ImageField(upload_to='movies/translations/covers', null=True, blank=True)

        def __str__(self):
            return f'{self.movie.title} ({self.language})'

    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    synopsis = models.TextField()
    release_date = models.DateField()
    cover = models.ImageField(upload_to='movies/covers', default='movies/covers/no-movie.png')
    directors = models.ManyToManyField('persons.Person', related_name='directed_movies')
    actors = models.ManyToManyField('persons.Person', related_name='acted_movies')
    genres = models.ManyToManyField('genres.Genre', related_name='movies')
    platforms = models.ManyToManyField('platforms.Platform', related_name='movies')
    awards = models.ManyToManyField('awards.Award', related_name='movies', blank=True)

    def __str__(self):
        return self.slug

    def translate_title(self, language):
        try:
            translation = self.translations.get(language=language)
        except self.MovieTranslation.DoesNotExist:
            translation = None
        if translation:
            return translation.title
        return self.title

    def translate_synopsis(self, language):
        try:
            translation = self.translations.get(language=language)
        except self.MovieTranslation.DoesNotExist:
            translation = None
        if translation:
            return translation.synopsis
        return self.synopsis

    def translate_image(self, language):
        try:
            translation = self.translations.get(language=language)
        except self.MovieTranslation.DoesNotExist:
            translation = None
        if translation and translation.image:
            return translation.image.url
        return self.cover.url
