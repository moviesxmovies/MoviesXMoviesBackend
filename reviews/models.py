from django.db import models

from shared.models import BaseModel


class Review(BaseModel):
    """
    A review of a cinematic work.

    Attributes:
        title (models.CharField): The title of the review.
        content (models.TextField): The content of the review.
        is_positive (models.BooleanField): Indicates if the review is positive or negative.
        user (models.ForeignKey): The user who wrote the review.
        movie (models.ForeignKey): The movie that the review is about.
    """

    title = models.CharField(max_length=128)
    content = models.TextField(max_length=256)
    is_positive = models.BooleanField()
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reviews')
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='reviews')

    class Meta:
        unique_together = ['user', 'movie']
        
    def __str__(self):
        return self.title
