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
