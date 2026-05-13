import logging

from django.core.cache import cache
from django.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Q,
    Value,
    When,
)
from django.utils.translation import gettext_lazy as _

from movielists.recommender import RecommenderModel
from movies.models import Movie
from ratings.models import Rating
from shared.models import BaseModel

logger = logging.getLogger(__name__)


class MovieList(BaseModel):
    """Model representing a list of movies created by a user.

    Attributes:
        name (models.CharField): The name of the movie list.
        slug (models.SlugField): URL-friendly identifier, unique per user.
        description (models.TextField): A brief description of the movie list.
        privacity (models.CharField): Visibility setting from ``Privacity``.
        user (models.ForeignKey): The user who created the movie list.
        movies (models.ManyToManyField): The movies included in the movie list.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'user'],
                name='unique_movielist_slug_user',
                violation_error_message=_('A movie list with this name already exists.'),
            )
        ]
        verbose_name = _('Movie List')
        verbose_name_plural = _('Movie Lists')

    class Privacity(models.TextChoices):
        """Privacy settings controlling who can view a movie list.

        Attributes:
            PUBLIC: The movie list is visible to everyone.
            FRIENDS: The movie list is visible to the creator's friends.
            PRIVATE: The movie list is only visible to the creator.
        """

        PUBLIC = 'P', 'Public'
        FRIENDS = 'F', 'Friends'
        PRIVATE = 'R', 'Private'

        class Meta:
            verbose_name = _('Privacy Setting')
            verbose_name_plural = _('Privacy Settings')

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128)
    description = models.TextField(blank=True)
    privacity = models.CharField(max_length=1, choices=Privacity, default=Privacity.PUBLIC)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='movies_lists')
    movies = models.ManyToManyField('movies.Movie', related_name='in_movie_lists', blank=True)

    def __str__(self) -> str:
        """Return the slug as the string representation of the list.

        Returns:
            str: The slug of the movie list.
        """
        return self.slug

    def intelligent_fill(
        self,
        genres: list[str] | None = None,
        celebrities: list[str] | None = None,
        friends: list[str] | None = None,
    ) -> None:
        """Populate the movie list using a scored recommendation pipeline.

        Excludes already watched or unseen-marked movies, applies hard
        filters (genre, platform), scores candidates by celebrities,
        friends' favourites, and awards, then sets the top 40 results
        on ``self.movies``.

        Args:
            genres (list[str] | None): Genre slugs to filter candidates by.
                Defaults to None.
            celebrities (list[str] | None): Celebrity slugs used to boost
                movies featuring those actors or directors. Defaults to None.
            friends (list[str] | None): Friend usernames whose highly-rated
                movies receive a score boost. Defaults to None.
        """
        exclude_ids = self._get_exclude_ids()
        candidates_qs = self._get_base_candidates(exclude_ids)
        candidates_qs = self._apply_hard_filters(candidates_qs, genres)

        scored_movies = self._score_candidates(candidates_qs, celebrities, friends)

        self.movies.set(scored_movies)

    def _get_exclude_ids(self) -> set[int]:
        """Return the set of movie PKs that should be excluded from recommendations.

        Combines movies the user has already rated with movies the user has
        explicitly marked as unseen.

        Returns:
            set[int]: Primary keys of movies to exclude.
        """
        watched = self.user.ratings.values_list('movie_id', flat=True)
        unseen = self.user.unseen_movies.values_list('id', flat=True)
        not_launched = Movie.objects.filter(release_date__gt=models.functions.Now()).values_list(
            'id', flat=True
        )
        return set(list(watched) + list(unseen) + list(not_launched))

    def _score_candidates(
        self,
        candidates_qs,
        celebrities: list[str] | None,
        friends: list[str] | None,
        limit: int = 50,
    ) -> models.QuerySet[Movie]:
        """Score and rank candidate movies using a weighted heuristic.

        Scoring weights applied per movie:

        - Base score: ``1.0``
        - Celebrity match (actor or director): ``+3.0``
        - In friends' favourites (rating ≥ 4): ``+2.5``
        - Has awards: ``+0.7``

        Args:
            candidates_qs: Queryset of candidate ``Movie`` instances to score.
            celebrities (list[str] | None): Celebrity slugs to match against
                each movie's actors and directors.
            friends (list[str] | None): Friend usernames whose favourites
                contribute to the score boost.

        Returns:
            list[tuple]: List of ``(Movie, float)`` tuples sorted by score
            in descending order.
        """
        friends_favs = self._get_friends_favorites(friends)

        has_als_rank = 'als_rank' in candidates_qs.query.annotations

        if celebrities:
            celeb_condition = Q(actors__slug__in=celebrities) | Q(directors__slug__in=celebrities)
        else:
            celeb_condition = Q(pk__in=[])

        qs = candidates_qs.annotate(
            award_count=Count('awards', distinct=True),
            heuristic_score=ExpressionWrapper(
                1.0
                + Case(When(celeb_condition, then=Value(3.0)), default=Value(0.0))
                + Case(When(id__in=friends_favs, then=Value(2.5)), default=Value(0.0))
                + Case(When(award_count__gt=0, then=Value(0.7)), default=Value(0.0)),
                output_field=FloatField(),
            ),
        )

        order_fields = ['-heuristic_score']
        if has_als_rank:
            order_fields.append('als_rank')
        else:
            fallback_field = (
                'popularity_score' if 'popularity_score' in qs.query.annotations else 'id'
            )
            order_fields.append(f'-{fallback_field}')

        return qs.order_by(*order_fields)[:limit]

    def _get_friends_favorites(self, friends_usernames: list[str] | None) -> list[int]:
        """Return the movie PKs rated 4 or higher by the specified friends.

        Args:
            friends_usernames (list[str] | None): Usernames of friends to
                query ratings for. Returns an empty list if ``None`` or empty.

        Returns:
            list[int]: Primary keys of movies rated ≥ 4 by the given friends.
        """
        if not friends_usernames:
            return []

        return list(
            Rating.objects.filter(user__username__in=friends_usernames, rating__gte=4).values_list(
                'movie_id', flat=True
            )
        )

    def _get_base_candidates(self, exclude_ids: set[int]):
        """Return a queryset of candidate movies for recommendation.

        Attempts to use the cached ALS model to generate personalised
        candidates. Falls back to a recency-ordered queryset of all
        non-excluded movies if the cache is empty, the user has no model
        mapping, or deserialisation fails.

        Args:
            exclude_ids (set[int]): Primary keys of movies to exclude from
                the candidate set.

        Returns:
            QuerySet: A ``Movie`` queryset of recommendation candidates.
        """
        raw_data = cache.get('movie_recommendation_model')

        if raw_data:
            try:
                data = RecommenderModel.get_data()
                if len(data['movie_id_map']) < 500:
                    logger.warning(
                        'ALS model has insufficient movies to generate recommendations. Actual count: %d',
                        len(data['movie_id_map']),
                    )
                    return self._get_fallback_candidates(exclude_ids)
                internal_id = data['user_id_map'].get(self.user.id)

                if internal_id is not None:
                    n_candidates = min(500 + len(exclude_ids), 1000)

                    ids, _ = data['model'].recommend(
                        internal_id,
                        data['user_items_matrix'][internal_id],
                        N=n_candidates,
                        filter_already_liked_items=False,
                    )

                    candidate_ids = [
                        data['reverse_movie_map'][i]
                        for i in ids
                        if i in data['reverse_movie_map']
                        and data['reverse_movie_map'][i] not in exclude_ids
                    ]
                    if candidate_ids:
                        preserved = Case(
                            *[When(id=pk, then=pos) for pos, pk in enumerate(candidate_ids)],
                            output_field=IntegerField(),
                        )
                        return (
                            Movie.objects.filter(id__in=candidate_ids)
                            .annotate(als_rank=preserved)
                            .order_by('als_rank')
                        )

            except Exception as e:
                logger.warning(f'ALS recommendation failed for user {self.user.id}: {e}')

        return self._get_fallback_candidates(exclude_ids)

    def _apply_hard_filters(self, queryset, genres: list[str] | None):
        """Apply mandatory filters to a candidate queryset.

        Prefetches related data, optionally restricts to the given genres,
        and filters by the user's subscribed platforms (including movies with
        no platform assigned). Returns at most 300 distinct results.

        Args:
            queryset: The base ``Movie`` queryset to filter.
            genres (list[str] | None): Genre slugs to restrict candidates to.
                No genre filter is applied when ``None`` or empty.

        Returns:
            QuerySet: Filtered and prefetched ``Movie`` queryset capped at 300.
        """
        qs = queryset.prefetch_related('actors', 'directors', 'awards', 'genres', 'platforms')

        if genres:
            qs = qs.filter(genres__slug__in=genres)

        user_platforms = list(self.user.platforms.values_list('slug', flat=True))
        if user_platforms:
            no_platform_ids = Movie.objects.filter(platforms=None).values_list('id', flat=True)
            qs = qs.filter(Q(platforms__slug__in=user_platforms) | Q(id__in=no_platform_ids))

        return qs.distinct()

    def _get_fallback_candidates(self, exclude_ids: set[int]):
        qs = Movie.objects.exclude(id__in=exclude_ids)

        user_ratings = self.user.ratings.filter(rating__gte=4).values_list('movie_id', flat=True)
        if user_ratings.exists():
            favourite_genre_ids = list(
                Movie.objects.filter(id__in=user_ratings)
                .values_list('genres__id', flat=True)
                .distinct()
            )
            favourite_genre_ids = [gid for gid in favourite_genre_ids if gid is not None]
            if favourite_genre_ids:
                qs = qs.filter(genres__id__in=favourite_genre_ids)

        return (
            qs.annotate(
                avg_rating=Avg('ratings__rating'),
                rating_count=Count('ratings'),
                popularity_score=ExpressionWrapper(
                    (F('avg_rating') * F('rating_count')) / (F('rating_count') + 10),
                    output_field=FloatField(),
                ),
                popularity_tmdb=F('popularity'),
            )
            .order_by('-popularity_tmdb', '-popularity_score', '-release_date')
            .distinct()
        )
