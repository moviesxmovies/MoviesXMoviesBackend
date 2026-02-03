from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from shared.models import BaseModel


class Rating(BaseModel):
    """
    Model representing a rating given by a user to a movie.

    Attributes:
        rating (models.PositiveSmallIntegerField): The rating given by the user.
        user (models.ForeignKey): The user who gave the rating.
        movie (models.ForeignKey): The movie that the rating is about.
    """

    MIN_RATING = 1
    MAX_RATING = 5
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)]
    )
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='ratings')
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='ratings')

    class Meta:
        unique_together = ['user', 'movie']
