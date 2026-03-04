import json
import pickle
from django.core.cache import cache
import pytest

from movies.serializers import MovieSerializer
from movies.tasks import retrain_professional_model
from ratings.models import Rating
from tests.conftest import (
    MOVIE_DETAIL_URL,
    MOVIE_FRIENDS_RATINGS_URL,
    MOVIE_REVIEWS_URL,
    MOVIE_SELF_RATING_URL,
)

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

    movie = movie_factory(
        title='Inception',
        directors=[director],
        genres=[genre],
        actors=[actor],
        platforms=[platform],
    )
    serialized = MovieSerializer(movie).serialize()

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
    assert serialized['actors'][0]['name'] == 'Leonardo DiCaprio'
    assert isinstance(serialized['directors'], list)
    assert len(serialized['directors']) == 1
    assert serialized['directors'][0]['name'] == 'Christopher Nolan'
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

    user1.following.add(user2)
    user2.following.add(user1)
    auth_client.user.following.add(user1)
    auth_client.user.following.add(user2)
    user1.following.add(auth_client.user)
    user2.following.add(auth_client.user)

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
    assert data['count'] == 3
    assert data['has_next'] is True
    assert data['has_previous'] is False
    assert data['current_page'] == 1
    assert data['total_pages'] == 2


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

    assert result == 'Modelo Implicit (ALS) entrenado exitosamente'
    
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