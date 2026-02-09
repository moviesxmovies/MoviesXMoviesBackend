import pytest
from movies.serializers import MovieSerializer
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
    movie_factory, person_factory, genre_factory, platform_factory
):
    director = person_factory(name='Christopher Nolan')
    genre = genre_factory(name='Sci-Fi')
    actor = person_factory(name='Leonardo DiCaprio')
    platform = platform_factory(name='Netflix')

    movie = movie_factory(
        directors=[director], genres=[genre], actors=[actor], platforms=[platform]
    )

    assert movie.directors.count() == 1
    assert movie.directors.first().name == 'Christopher Nolan'
    assert movie.genres.count() == 1
    assert movie.genres.first().name == 'Sci-Fi'


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