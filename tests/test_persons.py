import datetime
from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory

from persons.serializers import PersonSerializer
from tests.conftest import (
    PERSON_ACTED_MOVIES_URL,
    PERSON_ACTORS_SEARCH_URL,
    PERSON_ACTORS_SEARCHING_URL,
    PERSON_DIRECTED_MOVIES_URL,
    PERSON_DIRECTORS_SEARCH_URL,
    PERSON_DIRECTORS_SEARCHING_URL,
    PERSON_SEARCHING_URL,
)

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  PERSON
# ===========================================================================


@pytest.mark.django_db
def test_person_creation(person_factory):
    person = person_factory()
    assert person.name is not None
    assert person.slug is not None
    assert person.image is not None
    assert person.deleted_at is None
    assert person.created_at is not None
    assert person.updated_at is not None
    assert person.awards is not None


@pytest.mark.django_db
def test_person_build_does_not_add_relations(person_factory):
    person = person_factory.build()

    assert person.pk is None


@pytest.mark.django_db
def test_person_creation_with_extracted_relations(person_factory, award_factory):
    award = award_factory(name='Prime')

    person = person_factory(awards=[award])
    assert person.awards.count() == 1
    assert person.awards.first().name == 'Prime'


@pytest.mark.django_db
def test_person_str(person_factory):
    person = person_factory(name='John Doe', slug='john-doe')
    assert str(person) == 'john-doe'


# ===========================================================================
#  SERIALIZERS
# ===========================================================================
@pytest.mark.django_db
def test_person_serializer(person_factory):
    person = person_factory(
        name='John Doe',
        slug='john-doe',
        biography='A famous actor.',
        birthday=datetime.date(1980, 1, 1),
        deathday=datetime.date(2020, 1, 1),
        gender=1,
    )
    serialized = PersonSerializer(person).serialize()

    assert serialized['id'] == person.pk
    assert serialized['name'] == 'John Doe'
    assert serialized['slug'] == 'john-doe'
    assert serialized['image'] is not None
    assert serialized['awards'] is not None
    assert serialized['biography'] == 'A famous actor.'
    assert serialized['birthday'] == '1980-01-01'
    assert serialized['deathday'] == '2020-01-01'
    assert serialized['gender'] == 1


@pytest.mark.django_db
def test_person_serializer_with_translation(person_factory, person_translation_factory):
    translation_es = person_translation_factory(language='es', biography='Biografía en español')
    translation_fr = person_translation_factory(language='fr', biography='Biographie en français')

    person = person_factory(
        name='John Doe', slug='john-doe', translations=[translation_es, translation_fr]
    )

    request = RequestFactory().get('/')
    request.user = MagicMock(preferred_language='es')
    serialized = PersonSerializer(person, request=request).serialize()

    assert serialized['biography'] == 'Biografía en español'

    request.user.preferred_language = 'fr'
    serialized = PersonSerializer(person, request=request).serialize()
    assert serialized['biography'] == 'Biographie en français'


# ===========================================================================
#  VIEWS
# ===========================================================================
@pytest.mark.django_db
def test_person_detail_view(person_factory, auth_client):
    person = person_factory(name='John Doe', slug='john-doe')

    response = auth_client.get(f'/api/persons/{person.slug}/')
    assert response.status_code == 200
    data = response.json()

    assert data['id'] == person.pk
    assert data['name'] == 'John Doe'
    assert data['slug'] == 'john-doe'
    assert data['image'] is not None
    assert data['awards'] is not None


@pytest.mark.django_db
def test_person_actors_search_view(person_factory, auth_client, movie_factory):
    john = person_factory(name='John Doe', slug='john-doe')
    jane = person_factory(name='Jane Smith', slug='jane-smith')
    movie_factory(title='Movie 1', actors=[john], directors=[jane])

    response = auth_client.get(PERSON_ACTORS_SEARCH_URL)
    assert response.status_code == 200
    data = response.json()

    assert data['results'][0]['name'] == 'John Doe'


@pytest.mark.django_db
def test_person_directors_search_view(person_factory, auth_client, movie_factory):
    john = person_factory(name='John Doe', slug='john-doe')
    jane = person_factory(name='Jane Smith', slug='jane-smith')
    movie_factory(title='Movie 1', actors=[john], directors=[jane])

    response = auth_client.get(PERSON_DIRECTORS_SEARCH_URL)
    assert response.status_code == 200
    data = response.json()

    assert data['results'][0]['name'] == 'Jane Smith'


@pytest.mark.django_db
def test_person_actors_search_by_name(person_factory, auth_client, movie_factory):
    john = person_factory(name='John Doe', slug='john-doe')
    ruben = person_factory(name='Ruben Abreu', slug='ruben-abreu')
    movie_factory(
        title='Movie 1', actors=[john, ruben], directors=[], release_date=datetime.date(2020, 1, 1)
    )

    response = auth_client.get(PERSON_ACTORS_SEARCH_URL, {'name': 'Ruben Abreu'})
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Ruben Abreu'


@pytest.mark.django_db
def test_person_acted_movies_view(person_factory, auth_client, movie_factory):
    john = person_factory(name='John Doe', slug='john-doe')

    movie_factory(
        title='Movie 1', actors=[john], directors=[], release_date=datetime.date(2020, 1, 1)
    )
    movie_factory(
        title='Movie 2', actors=[john], directors=[], release_date=datetime.date(2020, 1, 1)
    )

    response = auth_client.get(PERSON_ACTED_MOVIES_URL.format(person_slug=john.slug))
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 2
    assert data['results'][0]['title'] == 'Movie 2'
    assert data['results'][1]['title'] == 'Movie 1'


@pytest.mark.django_db
def test_person_acted_movies_view_with_last_id(person_factory, auth_client, movie_factory):
    john = person_factory(name='John Doe', slug='john-doe')

    movie_factory(
        title='Movie 1', actors=[john], directors=[], release_date=datetime.date(2020, 1, 1)
    )
    movie2 = movie_factory(
        title='Movie 2', actors=[john], directors=[], release_date=datetime.date(2020, 2, 1)
    )
    movie3 = movie_factory(
        title='Movie 3', actors=[john], directors=[], release_date=datetime.date(2020, 3, 1)
    )

    response = auth_client.get(
        PERSON_ACTED_MOVIES_URL.format(person_slug=john.slug), {'last_id': movie3.pk, 'limit': 1}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['title'] == 'Movie 2'

    response2 = auth_client.get(
        PERSON_ACTED_MOVIES_URL.format(person_slug=john.slug), {'last_id': movie2.pk, 'limit': 1}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2['results']) == 1
    assert data2['results'][0]['title'] == 'Movie 1'


@pytest.mark.django_db
def test_person_directed_movies_view(person_factory, auth_client, movie_factory):
    jane = person_factory(name='Jane Smith', slug='jane-smith')

    movie_factory(
        title='Movie 1', actors=[], directors=[jane], release_date=datetime.date(2020, 1, 1)
    )
    movie_factory(
        title='Movie 2', actors=[], directors=[jane], release_date=datetime.date(2020, 2, 1)
    )

    response = auth_client.get(PERSON_DIRECTED_MOVIES_URL.format(person_slug=jane.slug))
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 2
    assert data['results'][0]['title'] == 'Movie 2'
    assert data['results'][1]['title'] == 'Movie 1'


@pytest.mark.django_db
def test_person_directed_movies_view_with_last_id(person_factory, auth_client, movie_factory):
    jane = person_factory(name='Jane Smith', slug='jane-smith')

    movie_factory(
        title='Movie 1', actors=[], directors=[jane], release_date=datetime.date(2020, 1, 1)
    )
    movie2 = movie_factory(
        title='Movie 2', actors=[], directors=[jane], release_date=datetime.date(2020, 2, 1)
    )

    movie3 = movie_factory(
        title='Movie 3', actors=[], directors=[jane], release_date=datetime.date(2020, 3, 1)
    )

    response = auth_client.get(
        PERSON_DIRECTED_MOVIES_URL.format(person_slug=jane.slug), {'last_id': movie3.pk, 'limit': 1}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['title'] == 'Movie 2'

    response2 = auth_client.get(
        PERSON_DIRECTED_MOVIES_URL.format(person_slug=jane.slug), {'last_id': movie2.pk, 'limit': 1}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2['results']) == 1
    assert data2['results'][0]['title'] == 'Movie 1'


@pytest.mark.django_db
def test_actors_search_view_with_no_query_returns_all(auth_client, person_factory, movie_factory):
    person1 = person_factory(name='John Doe', slug='john-doe')
    person2 = person_factory(name='Jane Smith', slug='jane-smith')

    movie_factory(
        title='Movie 1',
        actors=[person1, person2],
    )

    response = auth_client.get(PERSON_ACTORS_SEARCHING_URL)
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 2
    assert data['results'][0]['name'] == 'Jane Smith'
    assert data['results'][1]['name'] == 'John Doe'


@pytest.mark.django_db
def test_directors_search_view_with_no_query_returns_all(
    auth_client, person_factory, movie_factory
):
    person1 = person_factory(name='John Doe', slug='john-doe')
    person2 = person_factory(name='Jane Smith', slug='jane-smith')

    movie_factory(
        title='Movie 1',
        directors=[person1, person2],
    )

    response = auth_client.get(PERSON_DIRECTORS_SEARCHING_URL)
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 2
    assert data['results'][0]['name'] == 'Jane Smith'
    assert data['results'][1]['name'] == 'John Doe'


@pytest.mark.django_db
def test_actors_search_view_with_query_returns_filtered(auth_client, person_factory, movie_factory):
    person1 = person_factory(name='John Doe', slug='john-doe')
    person2 = person_factory(name='Jane Smith', slug='jane-smith')

    movie_factory(
        title='Movie 1',
        actors=[person1, person2],
    )

    response = auth_client.get(PERSON_ACTORS_SEARCHING_URL, {'search_query': 'Jane'})
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Jane Smith'


@pytest.mark.django_db
def test_directors_search_view_with_query_returns_filtered(
    auth_client, person_factory, movie_factory
):
    person1 = person_factory(name='John Doe', slug='john-doe')
    person2 = person_factory(name='Jane Smith', slug='jane-smith')

    movie_factory(
        title='Movie 1',
        directors=[person1, person2],
    )

    response = auth_client.get(PERSON_DIRECTORS_SEARCHING_URL, {'search_query': 'Jane'})
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Jane Smith'


@pytest.mark.django_db
def test_actors_search_view_with_query_and_last_id_returns_filtered_and_paginated(
    auth_client, person_factory, movie_factory
):
    person1 = person_factory(name='John Doe', slug='john-doe')
    person2 = person_factory(name='Jane Smith', slug='jane-smith')
    person3 = person_factory(name='Jane Doe', slug='jane-doe')

    movie_factory(
        title='Movie 1',
        actors=[person1, person2, person3],
    )

    response = auth_client.get(
        PERSON_ACTORS_SEARCHING_URL, {'search_query': 'Jane', 'last_id': person3.pk, 'limit': 1}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Jane Smith'


@pytest.mark.django_db
def test_directors_search_view_with_query_and_last_id_returns_filtered_and_paginated(
    auth_client, person_factory, movie_factory
):
    person1 = person_factory(name='John Doe', slug='john-doe')
    person2 = person_factory(name='Jane Smith', slug='jane-smith')
    person3 = person_factory(name='Jane Doe', slug='jane-doe')

    movie_factory(
        title='Movie 1',
        directors=[person1, person2, person3],
    )

    response = auth_client.get(
        PERSON_DIRECTORS_SEARCHING_URL, {'search_query': 'Jane', 'last_id': person3.pk, 'limit': 1}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Jane Smith'


@pytest.mark.django_db
def test_person_search_view_with_no_query_returns_all(auth_client, person_factory):
    person_factory(name='John Doe', slug='john-doe')
    person_factory(name='Jane Smith', slug='jane-smith')

    response = auth_client.get(PERSON_SEARCHING_URL)
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 2
    assert data['results'][0]['name'] == 'Jane Smith'
    assert data['results'][1]['name'] == 'John Doe'


@pytest.mark.django_db
def test_person_search_view_with_query_returns_filtered(auth_client, person_factory):
    person_factory(name='John Doe', slug='john-doe')
    person_factory(name='Jane Smith', slug='jane-smith')

    response = auth_client.get(PERSON_SEARCHING_URL, {'search_query': 'Jane'})
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Jane Smith'


@pytest.mark.django_db
def test_person_search_view_with_query_and_last_id_returns_filtered_and_paginated(
    auth_client, person_factory
):
    person_factory(name='John Doe', slug='john-doe')
    person_factory(name='Jane Smith', slug='jane-smith')
    person_factory(name='Jane Doe', slug='jane-doe')

    response = auth_client.get(
        PERSON_SEARCHING_URL, {'search_query': 'Jane', 'page': 2, 'limit': 1}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Jane Smith'