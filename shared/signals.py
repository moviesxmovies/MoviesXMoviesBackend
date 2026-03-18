from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from movies.models import Movie
from ratings.models import Rating
from reviews.models import Review
from users.models import User
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Movie)
def invalidate_movie_detail(sender, instance, **kwargs):
    cache.delete(f'movie_detail:{instance.pk}')
    logger.debug(f'Invalidated movie_detail cache for movie {instance.pk}')


@receiver(post_save, sender=Rating)
def invalidate_on_rating(sender, instance, created, **kwargs):
    if not created:
        return
    user = instance.user
    movie = instance.movie

    cache.delete(f'recommendations:{user.pk}')
    logger.debug(f'Invalidated recommendations cache for user {user.pk} due to new rating for movie {movie.pk}')

    for friend in user.friends.all():
        cache.delete(f'friends_ratings:{friend.pk}:{movie.pk}')
        logger.debug(f'Invalidated friends_ratings cache for friend {friend.pk} and movie {movie.pk}')


@receiver(post_save, sender=Review)
def invalidate_on_review(sender, instance, created, **kwargs):
    if not created:
        return
    logger.debug(f'Invalidating caches due to new review by user {instance.user.pk} for movie {instance.movie.pk}')
    cache.delete(f'recommendations:{instance.user.pk}')


@receiver(post_save, sender=User)
def invalidate_user_detail(sender, instance, **kwargs):
    cache.delete(f'user_detail:{instance.pk}')
    logger.debug(f'Invalidated user_detail cache for user {instance.pk}')
