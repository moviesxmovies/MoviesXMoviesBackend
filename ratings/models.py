from django.db import models
from shared.models import Timestamps
from django.core.validators import MaxValueValidator, MinValueValidator

class Rating(Timestamps):
    """
    Model representing a rating given by a user to a movie.
    
    Attributes:
        rating (models.PositiveSmallIntegerField): The rating given by the user.
        user (models.ForeignKey): The user who gave the rating.
        movie (models.ForeignKey): The movie that the rating is about.
    """
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='ratings'
    )
    movie = models.ForeignKey(
        'movies.Movie', 
        on_delete=models.CASCADE, 
        related_name='ratings'
    )
    
    class Meta:
        unique_together = ['user', 'movie']
