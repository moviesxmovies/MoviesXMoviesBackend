import pytest

from genres.serializers import GenreSerializer

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  GENRE
# ===========================================================================


@pytest.mark.django_db
def test_genre_creation(genre_factory):
    genre = genre_factory()
    assert genre.name is not None
    assert genre.slug is not None
    assert genre.deleted_at is None
    assert genre.created_at is not None
    assert genre.updated_at is not None


@pytest.mark.django_db
def test_genre_str(genre_factory):
    genre = genre_factory(name='Action')
    assert str(genre) == 'action'


# ===========================================================================
#  SERIALIZERS
# ===========================================================================


@pytest.mark.django_db
def test_genre_serializer(genre_factory):
    genre = genre_factory(name='Comedy')
    serialized = GenreSerializer(genre).serialize()

    assert serialized['id'] == genre.pk
    assert serialized['name'] == 'Comedy'
    assert serialized['slug'] == 'comedy'
