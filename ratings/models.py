from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from shared.models import BaseModel
from django.utils.translation import gettext_lazy as _


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
        verbose_name = _('Rating')
        verbose_name_plural = _('Ratings')
        unique_together = ['user', 'movie']

    def __str__(self):
        return f'{self.user}: {self.movie} | {self.rating}'
