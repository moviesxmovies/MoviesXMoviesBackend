import pytest
from reviews.serializers import ReviewSerializer

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  REVIEW
# ===========================================================================


@pytest.mark.django_db
def test_review_creation(review_factory):
    review = review_factory()
    assert review.title is not None
    assert review.user is not None
    assert review.movie is not None
    assert review.content is not None
    assert review.is_positive is not None
    assert review.deleted_at is None
    assert review.created_at is not None
    assert review.updated_at is not None


@pytest.mark.django_db
def test_review_str(review_factory):
    review = review_factory(title='Great movie!')
    assert str(review) == 'Great movie!'

# ===========================================================================
#  SERIALIZERS
# ===========================================================================
@pytest.mark.django_db
def test_review_serializer(review_factory):
    review = review_factory(title='Great movie!', content='I really enjoyed it.', is_positive=True)
    serialized = ReviewSerializer(review).serialize()

    assert serialized['id'] == review.pk
    assert serialized['title'] == 'Great movie!'
    assert serialized['movie'] == review.movie.slug
    assert serialized['user'] == review.user.username
    assert serialized['content'] == 'I really enjoyed it.'
    assert serialized['is_positive'] is True
    assert serialized['created_at'] == review.created_at.isoformat()
