import logging

from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from awards.models import Award
from movielists.models import MovieList
from movies.models import Movie
from persons.models import Person
from ratings.models import Rating
from reviews.models import Comment, Review
from users.models import FriendRequest, FriendShip, User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Movie)
def invalidate_movie_detail(sender, instance, **kwargs):
    cache.delete_many(keys=cache.keys(f'movie_detail:{instance.pk}:*'))
    logger.debug(f'Invalidated movie_detail cache for movie {instance.pk}')


@receiver(post_save, sender=Rating)
def invalidate_on_rating(sender, instance, created, **kwargs):
    if not created:
        return
    user = instance.user
    movie = instance.movie

    cache.delete_many(keys=cache.keys(f'recommendations:{user.pk}:*'))
    logger.debug(
        f'Invalidated recommendations cache for user {user.pk} due to new rating for movie {movie.pk}'
    )

    cache.delete(f'movie_rating:{user.pk}:{movie.pk}')
    logger.debug(f'Invalidated movie_rating cache for user {user.pk} and movie {movie.pk}')

    for friend in user.friends.all():
        cache.delete(f'friends_ratings:{friend.pk}:{movie.pk}')
        logger.debug(
            f'Invalidated friends_ratings cache for friend {friend.pk} and movie {movie.pk}'
        )


@receiver(post_save, sender=Review)
def invalidate_on_review(sender, instance, created, **kwargs):
    if not created:
        return
    logger.debug(
        f'Invalidating caches due to new review by user {instance.user.pk} for movie {instance.movie.pk}'
    )
    cache.delete(f'recommendations:{instance.user.pk}')
    cache.delete_many(keys=cache.keys(f'user_reviews:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movie_reviews:{instance.movie.pk}:*'))


@receiver(post_save, sender=User)
def invalidate_user_detail(sender, instance, **kwargs):
    cache.delete(f'user_detail:{instance.pk}')
    logger.debug(f'Invalidated user_detail cache for user {instance.pk}')
    cache.delete(f'self_user_detail:{instance.pk}')
    logger.debug(f'Invalidated self_user_detail cache for user {instance.pk}')


@receiver(post_save, sender=MovieList)
def invalidate_on_movielist(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of movie list {instance.pk} by user {instance.user.pk}'
    )
    cache.delete_many(keys=cache.keys(f'movies_lists_self:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movies_lists_detail:{instance.user.pk}:{instance.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movies_lists_user:{instance.user.pk}:*'))


@receiver(post_save, sender=Comment)
def invalidate_on_comment(sender, instance, created, **kwargs):
    if not created:
        return
    logger.debug(
        f'Invalidating caches due to new comment by user {instance.user.pk} for review {instance.review.pk}'
    )
    cache.delete_many(keys=cache.keys(f'review_comments:{instance.review.pk}:*'))


@receiver(post_save, sender=FriendShip)
def invalidate_on_friendship(sender, instance, created, **kwargs):
    if not created:
        return
    logger.debug(
        f'Invalidating caches due to new friendship between users {instance.user1.pk} and {instance.user2.pk}'
    )
    cache.delete_many(keys=cache.keys(f'user_friends:{instance.user1.pk}:*'))
    cache.delete_many(keys=cache.keys(f'user_friends:{instance.user2.pk}:*'))


@receiver(post_save, sender=Award)
def invalidate_on_award(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of award {instance.pk}'
    )
    cache.delete(f'award_detail:{instance.pk}')


@receiver(post_save, sender=Person)
def invalidate_on_person(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of person {instance.pk}'
    )
    cache.delete(f'person_detail:{instance.pk}')
