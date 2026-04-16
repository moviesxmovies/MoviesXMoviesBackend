import json
import pickle
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.utils import timezone

from movies.serializers import MovieSerializer
from movies.tasks import retrain_professional_model
from ratings.models import Rating
from tests.conftest import (
    MOVIE_DETAIL_URL,
    MOVIE_FRIENDS_RATINGS_URL,
    MOVIE_MOVIE_LISTS_URL,
    MOVIE_RECOMMENDATIONS_URL,
    MOVIE_REVIEWS_URL,
    MOVIE_SEARCHING_URL,
    MOVIE_SELF_RATING_URL,
    MOVIE_UNSEEN_URL,
)
from users.models import FriendShip

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  MOVIE
# ===========================================================================


@pytest.mark.django_db
def test_movie_creation(movie_factory):
    movie = movie_factory()
    assert movie.title is not None
    assert movie.slug is not None
    assert movie.synopsis is not None
    assert movie.release_date is not None
    assert movie.cover is not None
    assert movie.directors is not None
    assert movie.actors is not None
    assert movie.genres is not None
    assert movie.platforms is not None
    assert movie.deleted_at is None
    assert movie.created_at is not None
    assert movie.updated_at is not None


@pytest.mark.django_db
def test_movie_build_does_not_add_relations(movie_factory):
    movie = movie_factory.build()

    assert movie.pk is None


@pytest.mark.django_db
def test_movie_with_extracted_relations(
    movie_factory, person_factory, genre_factory, platform_factory, award_factory
):
    director = person_factory(name='Christopher Nolan')
    genre = genre_factory(name='Sci-Fi')
    actor = person_factory(name='Leonardo DiCaprio')
    platform = platform_factory(name='Netflix')
    award = award_factory(name='Prime')

    movie = movie_factory(
        directors=[director], genres=[genre], actors=[actor], platforms=[platform], awards=[award]
    )

    assert movie.directors.count() == 1
    assert movie.directors.first().name == 'Christopher Nolan'
    assert movie.genres.count() == 1
    assert movie.genres.first().name == 'Sci-Fi'
    assert movie.awards.count() == 1
    assert movie.awards.first().name == 'Prime'


@pytest.mark.django_db
def test_movie_str(movie_factory):
    movie = movie_factory(title='Inception')
    assert str(movie) == 'inception'


# ===========================================================================
#  SERIALIZERS
# ===========================================================================
@pytest.mark.django_db
def test_movie_serializer(movie_factory, person_factory, genre_factory, platform_factory):
    director = person_factory(name='Christopher Nolan')
    genre = genre_factory(name='Sci-Fi')
    actor = person_factory(name='Leonardo DiCaprio')
    platform = platform_factory(name='Netflix')
    request = RequestFactory().get('/')
    request.user = Mock(preferred_language='en')

    movie = movie_factory(
        title='Inception',
        directors=[director],
        genres=[genre],
        actors=[actor],
        platforms=[platform],
    )
    serialized = MovieSerializer(movie, request=request).serialize()

    assert serialized['id'] == movie.pk
    assert serialized['title'] == 'Inception'
    assert serialized['slug'] == 'inception'
    assert serialized['synopsis'] == movie.synopsis
    assert serialized['release_date'] == movie.release_date.isoformat()
    assert serialized['cover'] is not None
    assert isinstance(serialized['genres'], list)
    assert len(serialized['genres']) == 1
    assert serialized['genres'][0]['name'] == 'Sci-Fi'
    assert isinstance(serialized['actors'], list)
    assert len(serialized['actors']) == 1
    assert (
        serialized['actors'][0]
        == f'{request.scheme}://{request.get_host()}/api/persons/{actor.slug}/'
    )
    assert isinstance(serialized['directors'], list)
    assert len(serialized['directors']) == 1
    assert (
        serialized['directors'][0]
        == f'{request.scheme}://{request.get_host()}/api/persons/{director.slug}/'
    )
    assert isinstance(serialized['platforms'], list)
    assert len(serialized['platforms']) == 1
    assert serialized['platforms'][0]['name'] == 'Netflix'


@pytest.mark.django_db
def test_movie_serializer_with_translations(
    movie_factory, person_factory, genre_factory, platform_factory, movie_translation_factory
):
    director = person_factory(name='Christopher Nolan')
    genre = genre_factory(name='Sci-Fi')
    actor = person_factory(name='Leonardo DiCaprio')
    platform = platform_factory(name='Netflix')
    translation = movie_translation_factory(
        language='es',
        title='El Origen',
        synopsis='Una película sobre sueños dentro de sueños.',
    )
    movie = movie_factory(
        title='Inception',
        directors=[director],
        genres=[genre],
        actors=[actor],
        platforms=[platform],
        translations=[translation],
    )

    request = RequestFactory().get('/')
    request.user = Mock(preferred_language='es')

    serialized = MovieSerializer(movie, request=request).serialize()
    assert serialized['id'] == movie.pk
    assert serialized['title'] == translation.title
    assert serialized['slug'] == 'el-origen'
    assert serialized['synopsis'] == translation.synopsis
    assert serialized['release_date'] == movie.release_date.isoformat()
    assert serialized['cover'] is not None
    assert isinstance(serialized['genres'], list)
    assert len(serialized['genres']) == 1
    assert serialized['genres'][0]['name'] == 'Sci-Fi'
    assert isinstance(serialized['actors'], list)
    assert len(serialized['actors']) == 1
    assert (
        serialized['actors'][0]
        == f'{request.scheme}://{request.get_host()}/api/persons/{actor.slug}/'
    )
    assert isinstance(serialized['directors'], list)
    assert len(serialized['directors']) == 1
    assert (
        serialized['directors'][0]
        == f'{request.scheme}://{request.get_host()}/api/persons/{director.slug}/'
    )
    assert isinstance(serialized['platforms'], list)
    assert len(serialized['platforms']) == 1
    assert serialized['platforms'][0]['name'] == 'Netflix'


# ===========================================================================
# VIEWS
# ===========================================================================


@pytest.mark.django_db
def test_movie_detail_view(movie_factory, auth_client):
    movie = movie_factory(title='Inception')
    response = auth_client.get(MOVIE_DETAIL_URL.format(movie_slug=movie.slug))
    assert response.status_code == 200
    data = response.json()
    assert data['title'] == 'Inception'


@pytest.mark.django_db
def test_movie_friends_ratings_view(movie_factory, user_factory, rating_factory, auth_client):
    movie = movie_factory(title='Inception')
    user1 = user_factory()
    user2 = user_factory()
    rating_factory(movie=movie, user=user1, rating=4)
    rating_factory(movie=movie, user=user2, rating=5)

    FriendShip.objects.create(user1=auth_client.user, user2=user1)
    FriendShip.objects.create(user1=auth_client.user, user2=user2)

    response = auth_client.get(MOVIE_FRIENDS_RATINGS_URL.format(movie_slug=movie.slug))
    assert response.status_code == 200
    data = response.json()
    assert 'results' in data
    assert len(data['results']) == 2


@pytest.mark.django_db
def test_movie_friends_ratings_view_no_friends(movie_factory, auth_client):
    movie = movie_factory(title='Inception')
    response = auth_client.get(MOVIE_FRIENDS_RATINGS_URL.format(movie_slug=movie.slug))
    assert response.status_code == 200
    data = response.json()
    assert 'results' in data
    assert len(data['results']) == 0


@pytest.mark.django_db
def test_movie_reviews_view(movie_factory, review_factory, auth_client):
    movie = movie_factory(title='Inception')
    review_factory(movie=movie)
    review_factory(movie=movie)
    review_factory(movie=movie)

    response = auth_client.get(MOVIE_REVIEWS_URL.format(movie_slug=movie.slug) + '?page=1&limit=2')
    assert response.status_code == 200
    data = response.json()
    assert 'results' in data
    assert len(data['results']) == 2
    assert 'next_last_id' in data
    assert data['next_last_id'] is not None


@pytest.mark.django_db
def test_save_movie_review_view(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    review_data = {
        'title': 'Great movie!',
        'content': 'I really enjoyed it.',
        'is_positive': True,
    }

    response = auth_client.post(
        MOVIE_REVIEWS_URL.format(movie_slug=movie.slug),
        data=json.dumps(review_data),
        content_type='application/json',
    )
    assert response.status_code == 201
    data = response.json()
    assert data['title'] == 'Great movie!'
    assert data['content'] == 'I really enjoyed it.'
    assert data['is_positive'] is True


@pytest.mark.django_db
def test_movie_rating_view(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    rating_data = {
        'rating': 4,
    }

    response = auth_client.post(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(rating_data),
        content_type='application/json',
    )
    assert response.status_code == 201
    data = response.json()
    assert data['rating'] == 4


@pytest.mark.django_db
def test_movie_rating_view_invalid_rating(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    rating_data_above = {
        'rating': 7,
    }

    response = auth_client.post(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(rating_data_above),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.json()
    assert 'rating' in data
    assert 'Ensure this value is less than or equal to 5.' in str(data['rating'])

    rating_data_below = {
        'rating': 0,
    }
    response = auth_client.post(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(rating_data_below),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.json()
    assert 'rating' in data
    assert 'Ensure this value is greater than or equal to 1.' in str(data['rating'])


@pytest.mark.django_db
def test_movie_rating_view_already_exists(movie_factory, auth_client, rating_factory):
    movie = movie_factory(title='Inception')
    rating_factory(movie=movie, user=auth_client.user, rating=4)

    rating_data = {
        'rating': 5,
    }

    response = auth_client.post(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(rating_data),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'You have already rated this movie'


@pytest.mark.django_db
def test_movie_rating_view_update(movie_factory, auth_client, rating_factory):
    movie = movie_factory(title='Inception')
    rating_factory(movie=movie, user=auth_client.user, rating=4)

    # Update rating
    updated_rating_data = {
        'rating': 5,
    }
    response = auth_client.put(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(updated_rating_data),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.json()
    assert data['rating'] == 5


@pytest.mark.django_db
def test_movie_rating_view_update_invalid(movie_factory, auth_client, rating_factory):
    movie = movie_factory(title='Inception')
    rating_factory(movie=movie, user=auth_client.user, rating=4)

    # Update rating with invalid value
    updated_rating_data = {
        'rating': 0,
    }
    response = auth_client.put(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(updated_rating_data),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.json()
    assert 'rating' in data
    assert 'Ensure this value is greater than or equal to 1.' in str(data['rating'])


@pytest.mark.django_db
def test_movie_rating_view_update_not_exists(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    # Update rating that does not exist
    updated_rating_data = {
        'rating': 5,
    }
    response = auth_client.put(
        MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug),
        data=json.dumps(updated_rating_data),
        content_type='application/json',
    )
    assert response.status_code == 404
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'Rating not found'


@pytest.mark.django_db
def test_movie_rating_get_view(movie_factory, rating_factory, auth_client):
    movie = movie_factory(title='Inception')
    rating_factory(movie=movie, user=auth_client.user, rating=4)

    response = auth_client.get(MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug))
    assert response.status_code == 200
    data = response.json()
    assert data['rating'] == 4


@pytest.mark.django_db
def test_movie_rating_get_view_not_exists(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    response = auth_client.get(MOVIE_SELF_RATING_URL.format(movie_slug=movie.slug))
    assert response.status_code == 404
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'Rating not found'


# ===========================================================================
# TASKS
# ===========================================================================


@pytest.mark.django_db
def test_retrain_professional_model_success(user_factory, movie_factory, rating_factory):
    user_a = user_factory()
    user_b = user_factory()
    movie_1 = movie_factory()
    movie_2 = movie_factory()

    rating_factory(user=user_a, movie=movie_1, rating=5)
    rating_factory(user=user_b, movie=movie_2, rating=4)
    rating_factory(user=user_a, movie=movie_2, rating=2)

    result = retrain_professional_model()

    assert result == 'Model Implicit (ALS) trained'

    raw_data = cache.get('movie_recommendation_model')
    assert raw_data is not None

    data = pickle.loads(raw_data)

    assert 'model' in data
    assert 'user_id_map' in data
    assert 'movie_id_map' in data
    assert 'user_items_matrix' in data

    assert user_a.id in data['user_id_map']
    assert movie_1.id in data['movie_id_map']

    matrix = data['user_items_matrix']
    assert matrix.shape == (2, 2)
    assert matrix.sum() == 11.0

    cache.delete('movie_recommendation_model')


@pytest.mark.django_db
def test_retrain_model_no_ratings():
    Rating.objects.all().delete()

    result = retrain_professional_model()

    assert result == 'No ratings to train the model'
    assert cache.get('movie_recommendation_model') is None


# ===========================================================================
# Helpers
# ===========================================================================


def _setup_user_with_platform(user, movie_factory, platform_factory, count=1, **movie_kwargs):
    """
    _apply_hard_filters filters by user.platforms when the user has any.
    movie_factory always assigns a platform, so a platformless user matches
    nothing.  This helper creates a shared platform, attaches it to the user,
    and creates `count` movies on that platform so they survive the filter.
    """
    platform = platform_factory(name='TestPlatform')
    user.platforms.add(platform)
    movies = [movie_factory(platforms=[platform], **movie_kwargs) for _ in range(count)]
    return platform, movies


# ===========================================================================
# VIEWS - get_movie_recommendations
# ===========================================================================


@pytest.mark.django_db
def test_get_movie_recommendations_unauthenticated(client, movie_factory):
    """Unauthenticated requests should be rejected."""
    movie_factory()
    response = client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_get_movie_recommendations_empty(auth_client):
    """Returns an empty list when there are no movies in the DB."""
    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    assert results == []


@pytest.mark.django_db
def test_get_movie_recommendations_returns_movies(movie_factory, platform_factory, auth_client):
    """Returns a non-empty list when the user has a platform matching available movies."""
    _setup_user_with_platform(auth_client.user, movie_factory, platform_factory, count=3)

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0


@pytest.mark.django_db
def test_get_movie_recommendations_excludes_already_rated(
    movie_factory, platform_factory, rating_factory, auth_client
):
    """Movies the authenticated user has already rated must not appear."""
    platform = platform_factory(name='TestPlatform')
    auth_client.user.platforms.add(platform)

    rated_movie = movie_factory(title='Already Rated Movie', platforms=[platform])
    movie_factory(title='Fresh Movie', platforms=[platform])

    rating_factory(movie=rated_movie, user=auth_client.user, rating=4)

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    titles = [m['title'] for m in results]
    assert 'Already Rated Movie' not in titles
    assert 'Fresh Movie' in titles


@pytest.mark.django_db
def test_get_movie_recommendations_pagination(movie_factory, platform_factory, auth_client):
    """Results are capped at LIMIT_RECOMMENDATIONS regardless of how many movies exist."""
    from movies.views import LIMIT_RECOMMENDATIONS

    # Create more movies than the cap so the limit is actually exercised
    _setup_user_with_platform(
        auth_client.user, movie_factory, platform_factory, count=LIMIT_RECOMMENDATIONS + 5
    )

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) <= LIMIT_RECOMMENDATIONS


@pytest.mark.django_db
def test_get_movie_recommendations_boosts_friends_ratings(
    movie_factory, platform_factory, user_factory, rating_factory, auth_client
):
    """A movie rated highly by a mutual friend must surface in recommendations."""
    platform = platform_factory(name='TestPlatform')
    auth_client.user.platforms.add(platform)

    friend = user_factory()
    FriendShip.objects.create(user1=auth_client.user, user2=friend)

    # auth_client.user has NOT rated this — only the friend has
    friend_movie = movie_factory(title='Friend Loved This', platforms=[platform])
    movie_factory(title='Random Movie', platforms=[platform])

    rating_factory(movie=friend_movie, user=friend, rating=5)

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    titles = [m['title'] for m in results]
    assert 'Friend Loved This' in titles


@pytest.mark.django_db
def test_get_movie_recommendations_response_shape(movie_factory, platform_factory, auth_client):
    """Every recommended movie must contain all expected serializer fields."""
    _setup_user_with_platform(
        auth_client.user, movie_factory, platform_factory, count=1, title='Shape Test Movie'
    )

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0

    movie = results[0]
    for field in (
        'id',
        'title',
        'slug',
        'synopsis',
        'release_date',
        'cover',
        'genres',
        'actors',
        'directors',
        'platforms',
    ):
        assert field in movie, f'Missing field in response: {field}'


@pytest.mark.django_db
def test_get_movie_recommendations_no_model_in_cache_falls_back(
    movie_factory, platform_factory, auth_client
):
    """With no cached ML model the endpoint falls back to recency ordering."""
    from django.core.cache import cache

    cache.delete('movie_recommendation_model')

    platform = platform_factory(name='TestPlatform')
    auth_client.user.platforms.add(platform)
    movie_factory(title='Recency Fallback A', platforms=[platform])
    movie_factory(title='Recency Fallback B', platforms=[platform])

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 2


@pytest.mark.django_db
def test_get_movie_recommendations_pads_with_algorithmic_when_model_short(
    movie_factory, platform_factory, auth_client
):
    """With no cached model, padding fills results up to LIMIT_RECOMMENDATIONS."""
    from django.core.cache import cache

    cache.delete('movie_recommendation_model')

    _setup_user_with_platform(auth_client.user, movie_factory, platform_factory, count=20)

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0


@pytest.mark.django_db
def test_get_movie_recommendations_platform_filter(movie_factory, platform_factory, auth_client):
    """Only movies matching the user's platform survive _apply_hard_filters."""
    platform = platform_factory(name='Netflix')
    auth_client.user.platforms.add(platform)

    movie_factory(title='Netflix Movie', platforms=[platform])
    # This movie has a different platform — the user won't have it, so it's filtered out
    other_platform = platform_factory(name='HBO')
    movie_factory(title='HBO Only Movie', platforms=[other_platform])

    response = auth_client.get(MOVIE_RECOMMENDATIONS_URL)
    assert response.status_code == 200
    results = response.json()
    titles = [m['title'] for m in results]
    assert 'Netflix Movie' in titles
    assert 'HBO Only Movie' not in titles


# ===========================================================================
# _pad_with_algorithmic  (unit-level)
# ===========================================================================


@pytest.mark.django_db
def test_pad_with_algorithmic_fills_up_to_needed(movie_factory, platform_factory, user_factory):
    """Returns exactly `needed` movies when enough platform-matched movies exist."""
    from movies.views import _pad_with_algorithmic

    platform = platform_factory(name='TestPlatform')
    user = user_factory()
    user.platforms.add(platform)

    for _ in range(5):
        movie_factory(platforms=[platform])

    result = _pad_with_algorithmic([], set(), user, needed=5)
    assert len(result) == 5


@pytest.mark.django_db
def test_pad_with_algorithmic_does_not_duplicate_existing(
    movie_factory, platform_factory, user_factory
):
    """Movies already in `existing` are never added a second time."""
    from movies.views import _pad_with_algorithmic

    platform = platform_factory(name='TestPlatform')
    user = user_factory()
    user.platforms.add(platform)

    existing_movie = movie_factory(title='Already In List', platforms=[platform])
    for _ in range(4):
        movie_factory(platforms=[platform])

    result = _pad_with_algorithmic([existing_movie], set(), user, needed=5)
    ids = [m.id for m in result]
    assert ids.count(existing_movie.id) == 1


@pytest.mark.django_db
def test_pad_with_algorithmic_respects_exclude_ids(movie_factory, platform_factory, user_factory):
    """Movies whose IDs are in `exclude_ids` must never appear in the output."""
    from movies.views import _pad_with_algorithmic

    platform = platform_factory(name='TestPlatform')
    user = user_factory()
    user.platforms.add(platform)

    excluded = movie_factory(title='Excluded Movie', platforms=[platform])
    movie_factory(title='Allowed Movie', platforms=[platform])

    result = _pad_with_algorithmic([], {excluded.id}, user, needed=5)
    ids = [m.id for m in result]
    assert excluded.id not in ids


@pytest.mark.django_db
def test_pad_with_algorithmic_fewer_movies_than_needed(
    movie_factory, platform_factory, user_factory
):
    """Returns all available movies when fewer exist than `needed`."""
    from movies.views import _pad_with_algorithmic

    platform = platform_factory(name='TestPlatform')
    user = user_factory()
    user.platforms.add(platform)

    movie_factory(platforms=[platform])  # only 1 available

    result = _pad_with_algorithmic([], set(), user, needed=10)
    assert 1 <= len(result) <= 10


@pytest.mark.django_db
def test_pad_with_algorithmic_filters_by_user_platform(
    movie_factory, platform_factory, user_factory
):
    """Only platform-matched movies are returned when the user has platforms."""
    from movies.views import _pad_with_algorithmic

    user = user_factory()
    hbo = platform_factory(name='HBO')
    netflix = platform_factory(name='Netflix')
    user.platforms.add(hbo)

    movie_factory(title='HBO Movie', platforms=[hbo])
    movie_factory(title='Netflix Only', platforms=[netflix])

    result = _pad_with_algorithmic([], set(), user, needed=5)
    titles = [m.title for m in result]
    assert 'HBO Movie' in titles
    assert 'Netflix Only' not in titles


@pytest.mark.django_db
def test_pad_with_algorithmic_returns_existing_when_already_enough(
    movie_factory, platform_factory, user_factory
):
    """When `existing` already satisfies `needed`, no extra movies are appended."""
    from movies.views import _pad_with_algorithmic

    platform = platform_factory(name='TestPlatform')
    user = user_factory()
    user.platforms.add(platform)

    existing = [movie_factory(platforms=[platform]) for _ in range(5)]
    for _ in range(3):
        movie_factory(platforms=[platform])

    result = _pad_with_algorithmic(existing, set(), user, needed=5)

    assert len(result) == 5
    assert {m.id for m in result} == {m.id for m in existing}


@pytest.mark.django_db
def test_unseen_movie_view(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    response = auth_client.post(
        MOVIE_UNSEEN_URL.format(movie_slug=movie.slug),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success']
    auth_client.user.refresh_from_db()
    assert movie in auth_client.user.unseen_movies.all()


@pytest.mark.django_db
def test_unseen_movie_view_remove_unseen(movie_factory, auth_client):
    movie = movie_factory(title='Inception')
    auth_client.user.unseen_movies.add(movie)

    response = auth_client.delete(
        MOVIE_UNSEEN_URL.format(movie_slug=movie.slug),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success']
    auth_client.user.refresh_from_db()
    assert movie not in auth_client.user.unseen_movies.all()


@pytest.mark.django_db
def test_unseen_movie_view_already_unseen(movie_factory, auth_client):
    movie = movie_factory(title='Inception')
    auth_client.user.unseen_movies.add(movie)

    response = auth_client.post(
        MOVIE_UNSEEN_URL.format(movie_slug=movie.slug),
        content_type='application/json',
    )

    assert response.status_code == 400
    data = response.json()
    assert data['error'] == 'Movie already marked as unseen'
    auth_client.user.refresh_from_db()
    assert movie in auth_client.user.unseen_movies.all()


@pytest.mark.django_db
def test_unseen_movie_view_not_marked_unseen(movie_factory, auth_client):
    movie = movie_factory(title='Inception')

    response = auth_client.delete(
        MOVIE_UNSEEN_URL.format(movie_slug=movie.slug),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.json()
    assert data['error'] == 'Movie not marked as unseen'
    auth_client.user.refresh_from_db()
    assert movie not in auth_client.user.unseen_movies.all()


# ===========================================================================
# (VIEWS) movie_search
# ===========================================================================
@pytest.mark.django_db
class TestMovieSearchView:
    def test_search_by_name_and_translation(
        self, movie_factory, auth_client, movie_translation_factory
    ):
        user = auth_client.user
        user.preferred_language = 'es'
        user.save()

        the_great_war_es = movie_translation_factory(
            language='es',
            title='La Gran Guerra',
            synopsis='Una película sobre la Primera Guerra Mundial.',
        )

        movie_factory(title='The Great War', translations=[the_great_war_es])
        inception_es = movie_translation_factory(
            language='es',
            title='El Origen',
            synopsis='Una película sobre sueños dentro de sueños.',
        )
        movie_factory(title='Inception', translations=[inception_es])
        movie_factory(title='Inside Out')

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?name=Great')
        assert len(response.json()['results']) == 1

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?name=Origen')
        assert len(response.json()['results']) == 1

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?name=Vice-versa')
        assert len(response.json()['results']) == 0

    def test_search_by_relations(self, movie_factory, genre_factory, person_factory, auth_client):
        genre_action = genre_factory(slug='action')
        actor_pitt = person_factory(slug='brad-pitt')

        m1 = movie_factory(title='Action Movie')
        m1.genres.add(genre_action)
        m1.actors.add(actor_pitt)

        movie_factory(title='Drama Movie')

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?genres=action')
        assert len(response.json()['results']) == 1

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?actors=brad-pitt')
        assert len(response.json()['results']) == 1

    def test_search_marked_unseen(self, movie_factory, auth_client):
        user = auth_client.user
        m1 = movie_factory(title='Unseen')
        movie_factory(title='Seen')

        user.unseen_movies.add(m1)

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?marked_unseen=true')
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['id'] == m1.id

    def test_search_by_stars(self, movie_factory, rating_factory, auth_client):
        user = auth_client.user
        m1 = movie_factory()
        m2 = movie_factory()

        rating_factory(movie=m1, user=user, rating=5)
        rating_factory(movie=m2, user=user, rating=1)

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?stars=5')
        data = response.json()
        assert len(data['results']) == 1
        assert data['results'][0]['id'] == m1.id

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?stars=1&stars=5')
        assert len(response.json()['results']) == 2

    def test_search_reviewed(self, movie_factory, review_factory, auth_client):
        user = auth_client.user
        m1 = movie_factory()
        movie_factory()

        review_factory(movie=m1, user=user)

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?reviewed=true')
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['id'] == m1.id

    def test_search_pagination_and_order(self, movie_factory, auth_client):
        for i in range(15):
            movie_factory(
                title=f'Movie {i}', release_date=timezone.now().date() - timezone.timedelta(days=i)
            )

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?page=1&limit=10')
        data = response.json()
        assert len(data['results']) == 10
        assert data['count'] == 15

        assert data['results'][0]['release_date'] > data['results'][9]['release_date']

    def test_search_by_platforms(self, movie_factory, platform_factory, auth_client):
        platform_netflix = platform_factory(slug='netflix')
        platform_hbo = platform_factory(slug='hbo')

        m1 = movie_factory(title='Netflix Movie')
        m1.platforms.add(platform_netflix)

        movie_factory(title='HBO Movie').platforms.add(platform_hbo)

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?platforms=netflix')
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['id'] == m1.id

    def test_search_by_directors(self, movie_factory, person_factory, auth_client):
        director_nolan = person_factory(slug='christopher-nolan')
        director_spielberg = person_factory(slug='steven-spielberg')

        m1 = movie_factory(title='Nolan Movie')
        m1.directors.add(director_nolan)

        movie_factory(title='Spielberg Movie').directors.add(director_spielberg)

        response = auth_client.get(f'{MOVIE_SEARCHING_URL}?directors=christopher-nolan')
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['id'] == m1.id


@pytest.mark.django_db
def test_get_movie_lists_slug_user_movie(movie_factory, movie_list_factory, auth_client):
    movie = movie_factory(title='Inception')

    movie_list_factory(name='My List', user=auth_client.user, movies=[movie])
    movie_list_factory(name='Other List', user=auth_client.user, movies=[movie])

    response = auth_client.get(MOVIE_MOVIE_LISTS_URL.format(movie_slug=movie.slug))
    assert response.status_code == 200
    data = response.json()
    assert data[0] == 'my-list'
    assert data[1] == 'other-list'