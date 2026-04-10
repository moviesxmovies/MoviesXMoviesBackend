import pytest

from persons.serializers import PersonSerializer
from tests.conftest import PERSON_ACTORS_SEARCH_URL, PERSON_DIRECTORS_SEARCH_URL

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
    person = person_factory(name='John Doe', slug='john-doe')
    serialized = PersonSerializer(person).serialize()

    assert serialized['id'] == person.pk
    assert serialized['name'] == 'John Doe'
    assert serialized['slug'] == 'john-doe'
    assert serialized['image'] is not None
    assert serialized['awards'] is not None


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
    movie_factory(title='Movie 1', actors=[john, ruben], directors=[])

    response = auth_client.get(PERSON_ACTORS_SEARCH_URL, {'name': 'Ruben Abreu'})
    assert response.status_code == 200
    data = response.json()

    assert len(data['results']) == 1
    assert data['results'][0]['name'] == 'Ruben Abreu'
