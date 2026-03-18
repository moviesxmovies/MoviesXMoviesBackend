import pickle
from django.core.cache import cache
from django.db import models

from movies.models import Movie
from ratings.models import Rating
from shared.models import BaseModel
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


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
                violation_error_message=_('A movie list with this name already exists.')
            )
        ]
        verbose_name = _('Movie List')
        verbose_name_plural = _('Movie Lists')

    class Privacity(models.TextChoices):
        """Privacy settings controlling who can view a movie list.

        Attributes:
            PUBLIC: The movie list is visible to everyone.
            FOLLOWERS: The movie list is visible to the creator's followers.
            PRIVATE: The movie list is only visible to the creator.
        """

        PUBLIC = 'P', 'Public'
        FOLLOWERS = 'F', 'Followers'
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

        final_movies = [m for m, score in scored_movies[:40]]
        self.movies.set(final_movies)

    def _get_exclude_ids(self) -> set[int]:
        """Return the set of movie PKs that should be excluded from recommendations.

        Combines movies the user has already rated with movies the user has
        explicitly marked as unseen.

        Returns:
            set[int]: Primary keys of movies to exclude.
        """
        watched = self.user.ratings.values_list('movie_id', flat=True)
        unseen = self.user.unseen_movies.values_list('id', flat=True)
        return set(list(watched) + list(unseen))

    def _score_candidates(
        self,
        candidates_qs,
        celebrities: list[str] | None,
        friends: list[str] | None,
    ) -> list[tuple]:
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
        scored_list = []

        for movie in candidates_qs:
            score = 1.0

            if celebrities:
                celebs_in_movie = set(movie.actors.values_list('slug', flat=True)) | set(
                    movie.directors.values_list('slug', flat=True)
                )
                if any(c in celebs_in_movie for c in celebrities):
                    score += 3.0

            if movie.id in friends_favs:
                score += 2.5

            if movie.awards.exists():
                score += 0.7

            scored_list.append((movie, score))

        return sorted(scored_list, key=lambda x: x[1], reverse=True)

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
        raw_data = cache.get('movie_recommendation_model')

        if raw_data:
            try:
                data = pickle.loads(raw_data)
                dataset = data['dataset']

                user_mapping = dataset.mapping()[0]   
                item_mapping = dataset.mapping()[2]
                reverse_item = {v: k for k, v in item_mapping.items()}

                internal_uid = user_mapping.get(self.user.id)
                if internal_uid is not None:
                    n_items = len(item_mapping)
                    scores = data['model'].predict(
                        user_ids=internal_uid,
                        item_ids=list(range(n_items)),
                        item_features=data['item_features'],
                        user_features=data['user_features'],
                    )
                    top_ids = [
                        reverse_item[i]
                        for i in scores.argsort()[::-1]
                        if reverse_item.get(i) not in exclude_ids
                    ][:300]
                    return Movie.objects.filter(id__in=top_ids)
            except Exception:
                pass

        return Movie.objects.exclude(id__in=exclude_ids).order_by('-release_date')


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

        user_platforms = self.user.platforms.values_list('slug', flat=True)
        if user_platforms:
            qs = qs.filter(Q(platforms__slug__in=user_platforms) | Q(platforms__isnull=True))

        return qs.distinct()[:300]
