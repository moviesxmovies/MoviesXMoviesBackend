import pytest

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  RATING
# ===========================================================================


@pytest.mark.django_db
def test_rating_creation(rating_factory):
    rating = rating_factory()
    assert rating.user is not None
    assert rating.movie is not None
    assert rating.rating is not None
    assert rating.deleted_at is None
    assert rating.created_at is not None
    assert rating.updated_at is not None
