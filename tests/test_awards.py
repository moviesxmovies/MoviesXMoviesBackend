import pytest

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
