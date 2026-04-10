from unittest.mock import Mock

import pytest
from django.test import RequestFactory

from genres.serializers import GenreSerializer
from tests.conftest import GENRES_LIST_URL

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


@pytest.mark.django_db
def test_genre_serializer_with_translations(genre_factory, genre_translation_factory):
    translation = genre_translation_factory(language='es', name='Comedia')
    genre = genre_factory(name='Comedy', translations=[translation])
    request = RequestFactory().get('/')
    request.user = Mock(preferred_language='es')

    serialized = GenreSerializer(genre, request=request).serialize()

    assert serialized['id'] == genre.pk
    assert serialized['name'] == translation.name
    assert serialized['slug'] == 'comedy'


# ===========================================================================
#  VIEWS
# ===========================================================================


@pytest.mark.django_db
def test_genre_list_view( genre_factory, auth_client):
    genre_factory(name='Action')
    genre_factory(name='Comedy')

    response = auth_client.get(GENRES_LIST_URL)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['name'] == 'Action'
    assert data[1]['name'] == 'Comedy'
