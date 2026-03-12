from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


class Comment(BaseModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='comments')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    reply_comment = models.ForeignKey(
        'reviews.Comment', on_delete=models.CASCADE, related_name='replies', null=True, blank=True
    )

    def __str__(self):
        return f'{self.user} comments on {self.review}'


class Reaction(BaseModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reactions')

    class EmojiType(models.TextChoices):
        LIKE = '👍'
        LOVE = '❤️'
        LAUGH = '😂'
        SAD = '😢'
        FIRE = '🔥'
        EYES = '👀'
        POOP = '💩'
        SKULL = '💀'
        CLOWN = '🤡'
        MIND_BLOWN = '🤯'
        PARTY = '🥳'
        THINKING = '🤔'
        POPCORN = '🍿'
        STAR = '⭐'
        TOP = '🔝'
        TRASH = '🗑️'

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reactions')

    emoji = models.CharField(max_length=7, choices=EmojiType.choices, default=EmojiType.LIKE)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ['user', 'content_type', 'object_id', 'emoji']

    def __str__(self):
        return f'{self.user} reacted with {self.emoji} to {self.target}'
