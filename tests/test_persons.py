import pytest

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
    assert person.country is not None
    assert person.deleted_at is None
    assert person.created_at is not None
    assert person.updated_at is not None


@pytest.mark.django_db
def test_person_str(person_factory):
    person = person_factory(name='John Doe')
    assert str(person) == 'john-doe'
