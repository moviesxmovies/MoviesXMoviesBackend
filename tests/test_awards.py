import pytest

from awards.serializers import AwardSerializer

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  AWARD
# ===========================================================================


@pytest.mark.django_db
def test_award_creation(award_factory):
    award = award_factory()
    assert award.name is not None
    assert award.slug is not None
    assert award.category is not None
    assert award.date is not None
    assert award.icon is not None
    assert award.deleted_at is None
    assert award.created_at is not None
    assert award.updated_at is not None


@pytest.mark.django_db
def test_award_str(award_factory):
    award = award_factory(name='Special Award')
    assert str(award) == 'special-award'


# ===========================================================================
#  SERIALIZERS
# ===========================================================================


@pytest.mark.django_db
def test_award_serializer(award_factory):
    award = award_factory(name='Best Picture', category='BP')
    serialized = AwardSerializer(award).serialize()

    assert serialized['id'] == award.pk
    assert serialized['name'] == 'Best Picture'
    assert serialized['slug'] == 'best-picture'
    assert serialized['category'] == 'Best Picture'
    assert serialized['icon'] is not None
    assert serialized['date'] == award.date.isoformat() if award.date else None
