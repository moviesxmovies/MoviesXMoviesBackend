import pytest

from persons.serializers import PersonSerializer

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
