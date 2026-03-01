import json

from django.urls import reverse
import pytest
from reviews.models import Review
from reviews.serializers import ReviewSerializer
from tests.conftest import EDIT_DELETE_REVIEW_URL

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
    assert serialized['user'].endswith(reverse('user-detail', args=[review.user]))
    assert serialized['movie'].endswith(reverse('movies:movie-detail', args=[review.movie]))
    assert serialized['content'] == 'I really enjoyed it.'
    assert serialized['is_positive'] is True
    assert serialized['created_at'] == review.created_at.isoformat()


# ===========================================================================
#  VIEWS
# ===========================================================================

@pytest.mark.django_db
def test_review_edit(review_factory, auth_client):
    review = review_factory(title='Great movie!', content='I really enjoyed it.', is_positive=True, user=auth_client.user)

    response = auth_client.put(EDIT_DELETE_REVIEW_URL.format(review_id=review.pk), data=json.dumps({
        'title': 'Not so great',
        'content': 'I changed my mind.',
        'is_positive': False,
    }), content_type='application/json')

    

    assert response.status_code == 200
    assert response.json()['id'] == review.pk
    assert response.json()['title'] == 'Not so great'
    assert response.json()['content'] == 'I changed my mind.'
    assert response.json()['is_positive'] is False
    review.refresh_from_db()
    assert review.title == 'Not so great'
    assert review.content == 'I changed my mind.'
    assert review.is_positive is False
    assert review.deleted_at is None
    assert review.created_at is not None
    assert review.updated_at is not None

@pytest.mark.django_db
def test_review_edit_forbidden(review_factory, auth_client):
    review = review_factory(title='Great movie!', content='I really enjoyed it.', is_positive=True)

    response = auth_client.put(EDIT_DELETE_REVIEW_URL.format(review_id=review.pk), data=json.dumps({
        'title': 'Not so great',
        'content': 'I changed my mind.',
        'is_positive': False,
    }), content_type='application/json')

    assert response.status_code == 403
    review.refresh_from_db()
    assert review.title == 'Great movie!'
    assert review.content == 'I really enjoyed it.'
    assert review.is_positive is True
    assert review.deleted_at is None
    assert review.created_at is not None
    assert review.updated_at is not None

@pytest.mark.django_db
def test_review_delete(review_factory, auth_client):
    review = review_factory(user=auth_client.user)

    response = auth_client.delete(EDIT_DELETE_REVIEW_URL.format(review_id=review.pk))

    assert response.status_code == 204
    review.refresh_from_db()
    assert review.deleted_at is not None
    assert not Review.objects.filter(pk=review.pk).exists()

@pytest.mark.django_db
def test_review_delete_forbidden(review_factory, auth_client):
    review = review_factory()

    response = auth_client.delete(EDIT_DELETE_REVIEW_URL.format(review_id=review.pk))

    assert response.status_code == 403
    review.refresh_from_db()
    assert review.deleted_at is None
    assert Review.objects.filter(pk=review.pk).exists()