import pytest

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  REVIEW
# ===========================================================================


@pytest.mark.django_db
def test_review_creation(review_factory):
    review = review_factory()
    assert review.user is not None
    assert review.movie is not None
    assert review.content is not None
    assert review.isPositive is not None
    assert review.deleted_at is None
    assert review.created_at is not None
    assert review.updated_at is not None
