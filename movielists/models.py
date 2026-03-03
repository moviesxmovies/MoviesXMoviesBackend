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
        """
        Sistema Híbrido Avanzado:
        1. Generación de candidatos con ML (Implicit).
        2. Exclusión de contenido ya interactuado (Ratings + Unseen).
        3. Re-ranking por metadatos, red social y plataformas del usuario.
        """
        user = self.user

        watched_ids = user.ratings.values_list('movie_id', flat=True)
        unseen_ids = user.unseen_movies.values_list('id', flat=True)

        exclude_ids = set(list(watched_ids) + list(unseen_ids))

        raw_data = cache.get('movie_recommendation_model')

        if raw_data:
            data = pickle.loads(raw_data)
            model = data['model']
            user_id_map = data['user_id_map']
            reverse_movie_map = data['reverse_movie_map']
            user_items_matrix = data['user_items_matrix']

            internal_user_id = user_id_map.get(user.id)

            if internal_user_id is not None:
                ids, _ = model.recommend(
                    internal_user_id, user_items_matrix[internal_user_id], N=300
                )
                candidate_ids = [
                    reverse_movie_map[i] for i in ids if reverse_movie_map[i] not in exclude_ids
                ]
                candidates_qs = Movie.objects.filter(id__in=candidate_ids)
            else:
                candidates_qs = Movie.objects.exclude(id__in=exclude_ids).order_by('-release_date')[
                    :300
                ]
        else:
            candidates_qs = Movie.objects.exclude(id__in=exclude_ids).order_by('-release_date')[
                :300
            ]

        candidates_qs = candidates_qs.prefetch_related(
            'actors', 'directors', 'awards', 'genres', 'platforms'
        )

        if genres:
            candidates_qs = candidates_qs.filter(genres__slug__in=genres).distinct()

        user_platforms = list(user.platforms.values_list('slug', flat=True))
        if user_platforms:
            candidates_qs = candidates_qs.filter(platforms__slug__in=user_platforms).distinct()

        scored_recommendations = []

        friends_favorites = []
        if friends:
            from ratings.models import Rating

            friends_favorites = list(
                Rating.objects.filter(user__username__in=friends, rating__gte=4).values_list(
                    'movie_id', flat=True
                )
            )

        for movie in candidates_qs:
            score = 1.0

            if celebrities:
                movie_celebs = list(movie.actors.values_list('slug', flat=True)) + list(
                    movie.directors.values_list('slug', flat=True)
                )
                if any(c in movie_celebs for c in celebrities):
                    score += 3.0

            if movie.id in friends_favorites:
                score += 2.5

            if movie.awards.exists():
                score += 0.7

            if movie.release_date and hasattr(user, 'favorite_decade'):
                movie_decade = (movie.release_date.year // 10) * 10
                if movie_decade == user.favorite_decade:
                    score += 0.5

            scored_recommendations.append((movie, score))

        scored_recommendations.sort(key=lambda x: x[1], reverse=True)

        final_movies = [item[0] for item in scored_recommendations[:40]]
        self.movies.set(final_movies)
