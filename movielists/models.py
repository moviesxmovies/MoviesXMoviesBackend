import pickle
from django.core.cache import cache
from django.db import models

from movies.models import Movie
from shared.models import BaseModel


class MovieList(BaseModel):
    """
    Model representing a list of movies created by a user.

    Attributes:
        name (models.CharField): The name of the movie list.
        description (models.TextField): A brief description of the movie list.
        user (models.ForeignKey): The user who created the movie list.
        movies (models.ManyToManyField): The movies included in the movie list.
    """

    class Meta:
        unique_together = ('slug', 'user')

    class Privacity(models.TextChoices):
        """
        Enumeration for the privacy settings of the movie list.
        1. PUBLIC: The movie list is visible to everyone.
        2. FOLLOWERS: The movie list is visible to the creator's followers.
        3. PRIVATE: The movie list is only visible to the creator.
        """

        PUBLIC = 'P', 'Public'
        FOLLOWERS = 'F', 'Followers'
        PRIVATE = 'R', 'Private'

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128)
    description = models.TextField(blank=True)
    privacity = models.CharField(max_length=1, choices=Privacity, default=Privacity.PUBLIC)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='movies_lists')
    movies = models.ManyToManyField('movies.Movie', related_name='in_movie_lists', blank=True)

    def __str__(self):
        return self.slug

    def intelligent_fill(self, genres=None, celebrities=None, friends=None):
        exclude_ids = self._get_exclude_ids()
        candidates_qs = self._get_base_candidates(exclude_ids)

        candidates_qs = self._apply_hard_filters(candidates_qs, genres)

        scored_movies = self._score_candidates(candidates_qs, celebrities, friends)

        final_movies = [m for m, score in scored_movies[:40]]
        self.movies.set(final_movies)

    def _get_exclude_ids(self):
        watched = self.user.ratings.values_list('movie_id', flat=True)
        unseen = self.user.unseen_movies.values_list('id', flat=True)
        return set(list(watched) + list(unseen))

    def _score_candidates(self, candidates_qs, celebrities, friends):
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

            if self._is_from_favorite_decade(movie):
                score += 0.5

            scored_list.append((movie, score))

        return sorted(scored_list, key=lambda x: x[1], reverse=True)

    def _get_friends_favorites(self, friends_usernames):
        if not friends_usernames:
            return []
        from ratings.models import Rating

        return list(
            Rating.objects.filter(user__username__in=friends_usernames, rating__gte=4).values_list(
                'movie_id', flat=True
            )
        )

    def _is_from_favorite_decade(self, movie):
        fav_decade = getattr(self.user, 'favorite_decade', None)
        if movie.release_date and fav_decade:
            return (movie.release_date.year // 10) * 10 == fav_decade
        return False

    def _get_base_candidates(self, exclude_ids):

        raw_data = cache.get('movie_recommendation_model')

        if raw_data:
            try:
                data = pickle.loads(raw_data)
                internal_id = data['user_id_map'].get(self.user.id)

                if internal_id is not None:
                    ids, _ = data['model'].recommend(
                        internal_id, data['user_items_matrix'][internal_id], N=300
                    )
                    candidate_ids = [
                        data['reverse_movie_map'][i]
                        for i in ids
                        if data['reverse_movie_map'][i] not in exclude_ids
                    ]
                    return Movie.objects.filter(id__in=candidate_ids)
            except Exception:
                pass

        return Movie.objects.exclude(id__in=exclude_ids).order_by('-release_date')

    def _apply_hard_filters(self, queryset, genres):
        qs = queryset.prefetch_related('actors', 'directors', 'awards', 'genres', 'platforms')

        if genres:
            qs = qs.filter(genres__slug__in=genres)

        user_platforms = self.user.platforms.values_list('slug', flat=True)
        if user_platforms:
            qs = qs.filter(platforms__slug__in=user_platforms)

        return qs.distinct()[:300]
