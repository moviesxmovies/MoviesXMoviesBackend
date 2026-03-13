from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from shared.models import BaseModel
from users.models import User


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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='reviews')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'movie'],
                condition=models.Q(deleted_at=None),
                name='unique_active_review_per_user_movie',
                violation_error_message=_('Each user can only have one active review per movie.'),
            )
        ]

    def get_absolute_url(self):
        return reverse('reviews:movie-reviews', args=[self.pk])

    def __str__(self):
        return self.title


class Comment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    reply_comment = models.ForeignKey(
        'reviews.Comment', on_delete=models.CASCADE, related_name='replies', null=True, blank=True
    )

    def get_absolute_url(self):
        return reverse('reviews:comment-wrapper', args=[self.review.pk, self.pk])

    def __str__(self):
        return f'{self.pk}: {self.user} comments on {self.review}'


class Reaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')

    class EmojiType(models.TextChoices):
        LIKE = 'LIKE', '👍'
        LOVE = 'LOVE', '❤️'
        LAUGH = 'LAUGH', '😂'
        SAD = 'SAD', '😢'
        FIRE = 'FIRE', '🔥'
        EYES = 'EYES', '👀'
        POOP = 'POOP', '💩'
        SKULL = 'SKULL', '💀'
        CLOWN = 'CLOWN', '🤡'
        MIND_BLOWN = 'MIND_BLOWN', '🤯'
        PARTY = 'PARTY', '🥳'
        THINKING = 'THINKING', '🤔'
        POPCORN = 'POPCORN', '🍿'
        STAR = 'STAR', '⭐'
        TOP = 'TOP', '🔝'
        TRASH = 'TRASH', '🗑️'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')

    emoji = models.CharField(max_length=20, choices=EmojiType.choices)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ['user', 'content_type', 'object_id', 'emoji']

    def __str__(self):
        return f'{self.user} reacted with {self.emoji} to {self.target}'
