import logging

from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from awards.models import Award
from genres.models import Genre
from movielists.models import MovieList
from movies.models import Movie
from persons.models import Person
from platforms.models import Platform
from ratings.models import Rating
from reviews.models import Comment, Reaction, Review
from users.models import FriendShip, User

logger = logging.getLogger(__name__)
MOVIE_SEARCH_ALL = 'movie_search:*'


@receiver(post_save, sender=Reaction)
def invalidate_reaction_caches(sender, instance, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if instance._state.adding else "update"} of reaction {instance.pk} by user {instance.user.pk}'
    )
    if instance.content_type.model == 'review':
        cache.delete(f'review_reactions:{instance.object_id}')
        logger.debug(f'Invalidated review_reactions cache for review {instance.object_id}')
    elif instance.content_type.model == 'comment':
        cache.delete(f'comment_reactions:{instance.object_id}')
        logger.debug(f'Invalidated comment_reactions cache for comment {instance.object_id}')


@receiver(m2m_changed, sender=Movie.actors.through)
def invalidate_actor_movies_on_change(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear'] and pk_set:
        for actor_pk in pk_set:
            cache.delete_many(keys=cache.keys(f'person_acted_movies:{actor_pk}:*'))
            logger.debug(f'Invalidated acted_movies for actor {actor_pk}')


@receiver(m2m_changed, sender=Movie.directors.through)
def invalidate_director_movies_on_change(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear'] and pk_set:
        for director_pk in pk_set:
            cache.delete_many(keys=cache.keys(f'person_directed_movies:{director_pk}:*'))
            logger.debug(f'Invalidated directed_movies for director {director_pk}')


@receiver(m2m_changed, sender=Movie.genres.through)
def invalidate_movie_genres_on_change(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete_many(keys=cache.keys(f'movie_detail:{instance.pk}:*'))

        cache.delete_many(keys=cache.keys(MOVIE_SEARCH_ALL))


@receiver(m2m_changed, sender=Movie.platforms.through)
def invalidate_movie_platforms_on_change(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete_many(keys=cache.keys(f'movie_detail:{instance.pk}:*'))
        cache.delete_many(keys=cache.keys(MOVIE_SEARCH_ALL))


@receiver(m2m_changed, sender=Movie.awards.through)
def invalidate_movie_awards_on_change(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete_many(keys=cache.keys(f'movie_detail:{instance.pk}:*'))


@receiver(post_save, sender=Movie)
def invalidate_movie_detail(sender, instance, **kwargs):
    cache.delete_many(keys=cache.keys(f'movie_detail:{instance.pk}:*'))
    logger.debug(f'Invalidated movie_detail cache for movie {instance.pk}')

    cache.delete_many(keys=cache.keys(MOVIE_SEARCH_ALL))
    logger.debug(f'Invalidated movie_search cache due to update of movie {instance.pk}')


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

    cache.delete_many(keys=cache.keys(MOVIE_SEARCH_ALL))
    logger.debug(f'Invalidated movie_search cache for user {user.pk} by rating movie {movie.pk}')

    cache.delete_many(keys=cache.keys(f'friends_ratings:{user.pk}:{movie.pk}:*'))
    logger.debug(
        f'Invalidated friends_ratings cache for user {user.pk} and movie {movie.pk} due to new rating'
    )


@receiver(post_save, sender=Review)
def invalidate_on_review(sender, instance, created, **kwargs):
    if not created:
        return
    logger.debug(
        f'Invalidating caches due to new review by user {instance.user.pk} for movie {instance.movie.pk}'
    )
    cache.delete_many(keys=cache.keys(f'recommendations:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'user_reviews:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movie_reviews:{instance.movie.pk}:*'))


@receiver(post_save, sender=User)
def invalidate_user_detail(sender, instance, **kwargs):
    cache.delete(f'user_detail:{instance.pk}')
    logger.debug(f'Invalidated user_detail cache for user {instance.pk}')

    cache.delete(f'self_user_detail:{instance.pk}')
    logger.debug(f'Invalidated self_user_detail cache for user {instance.pk}')

    cache.delete_many(keys=cache.keys('user_search:*'))
    logger.debug(f'Invalidated user_search cache due to update of user {instance.pk}')


@receiver(post_save, sender=MovieList)
def invalidate_on_movielist(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of movie list {instance.pk} by user {instance.user.pk}'
    )
    cache.delete_many(keys=cache.keys(f'movies_lists_self:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movies_lists_detail:{instance.user.pk}:{instance.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movies_lists_user:{instance.user.pk}:*'))


@receiver(m2m_changed, sender=MovieList.movies.through)
def invalidate_on_movielist_movies_change(sender, instance, **kwargs):
    logger.debug(
        f'Invalidating caches due to change in movies for movie list {instance.pk} by user {instance.user.pk}'
    )
    cache.delete_many(keys=cache.keys(f'movies_lists_self:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movies_lists_detail:{instance.user.pk}:{instance.pk}:*'))
    cache.delete_many(keys=cache.keys(f'movies_lists_user:{instance.user.pk}:*'))
    cache.delete_many(keys=cache.keys(f'self_movie_lists_slug:{instance.user.pk}:*'))


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

    cache.delete_many(keys=cache.keys(f'friends_ratings:{instance.user1.pk}:*'))
    cache.delete_many(keys=cache.keys(f'friends_ratings:{instance.user2.pk}:*'))
    logger.debug(
        f'Invalidated friends_ratings cache for user {instance.user1.pk} and user {instance.user2.pk} due to new friendship'
    )


@receiver(post_save, sender=Award)
def invalidate_on_award(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of award {instance.pk}'
    )
    cache.delete(f'award_detail:{instance.pk}')


@receiver(m2m_changed, sender=Person.awards.through)
def invalidate_person_awards_on_change(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete_many(keys=cache.keys(f'person_detail:{instance.pk}:*'))


@receiver(post_save, sender=Person)
def invalidate_on_person(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of person {instance.pk}'
    )
    cache.delete_many(keys=cache.keys(f'person_detail:{instance.pk}:*'))

    cache.delete_many(keys=cache.keys('actor_pagination:*'))
    cache.delete_many(keys=cache.keys('director_pagination:*'))


@receiver(post_save, sender=Genre)
def invalidate_on_genre(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of genre {instance.pk}'
    )
    cache.delete_many(keys=cache.keys('genre_list:*'))


@receiver(post_save, sender=Platform)
def invalidate_on_platform(sender, instance, created, **kwargs):
    logger.debug(
        f'Invalidating caches due to {"creation" if created else "update"} of platform {instance.pk}'
    )
    cache.delete('platform_list')
