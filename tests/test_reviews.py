import json
from unittest import mock
from unittest.mock import MagicMock

import deepl
import pytest
from django.urls import reverse

from reviews.models import Comment, Reaction, Review
from reviews.serializers import ReviewSerializer
from reviews.views import __translate_text
from tests.conftest import (
    COMMENT_REACTION_DETAIL_URL,
    COMMENT_REACTIONS_URL,
    REVIEW_COMMENT_DETAIL_URL,
    REVIEW_COMMENT_REPLIES_URL,
    REVIEW_COMMENT_TRANSLATIONS_URL,
    REVIEW_COMMENTS_URL,
    REVIEW_REACTION_DETAIL_URL,
    REVIEW_REACTIONS_URL,
    REVIEW_TRANSLATIONS_URL,
    REVIEW_WRAPPER_URL,
)


@pytest.fixture
def mock_reviews_deepl():
    with mock.patch('reviews.views.translator') as mock_translator:
        mock_result = mock.MagicMock()
        mock_result.text = '¡Gran película!'
        mock_translator.translate_text.return_value = mock_result
        yield mock_translator


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
    review = review_factory(
        title='Great movie!',
        content='I really enjoyed it.',
        is_positive=True,
        user=auth_client.user,
    )

    response = auth_client.put(
        REVIEW_WRAPPER_URL.format(review_id=review.pk),
        data=json.dumps(
            {
                'title': 'Not so great',
                'content': 'I changed my mind.',
                'is_positive': False,
            }
        ),
        content_type='application/json',
    )

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

    response = auth_client.put(
        REVIEW_WRAPPER_URL.format(review_id=review.pk),
        data=json.dumps(
            {
                'title': 'Not so great',
                'content': 'I changed my mind.',
                'is_positive': False,
            }
        ),
        content_type='application/json',
    )

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

    response = auth_client.delete(REVIEW_WRAPPER_URL.format(review_id=review.pk))

    assert response.status_code == 204
    review.refresh_from_db()
    assert review.deleted_at is not None
    assert not Review.objects.filter(pk=review.pk).exists()


@pytest.mark.django_db
def test_review_delete_forbidden(review_factory, auth_client):
    review = review_factory()

    response = auth_client.delete(REVIEW_WRAPPER_URL.format(review_id=review.pk))

    assert response.status_code == 403
    review.refresh_from_db()
    assert review.deleted_at is None
    assert Review.objects.filter(pk=review.pk).exists()


from django.contrib.contenttypes.models import ContentType

# ===========================================================================
#  COMMENTS
# ===========================================================================


@pytest.mark.django_db
def test_create_comment(review_factory, auth_client):
    review = review_factory()
    response = auth_client.post(
        REVIEW_COMMENTS_URL.format(review_id=review.pk),
        data=json.dumps({'content': 'Great review!'}),
        content_type='application/json',
    )
    assert response.status_code == 201
    assert response.json()['content'] == 'Great review!'
    assert Comment.objects.filter(review=review).count() == 1


@pytest.mark.django_db
def test_create_comment_unauthenticated(review_factory, client):
    review = review_factory()
    response = client.post(
        REVIEW_COMMENTS_URL.format(review_id=review.pk),
        data=json.dumps({'content': 'Great review!'}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_get_review_comments(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment_factory(review=review)
    comment_factory(review=review)
    response = auth_client.get(REVIEW_COMMENTS_URL.format(review_id=review.pk))
    assert response.status_code == 200
    assert len(response.json()['results']) == 2


@pytest.mark.django_db
def test_get_review_comments_pagination(review_factory, comment_factory, auth_client):
    review = review_factory()
    comments = [comment_factory(review=review) for _ in range(5)]
    response = auth_client.get(REVIEW_COMMENTS_URL.format(review_id=review.pk) + '?limit=3')
    data = response.json()
    assert response.status_code == 200
    assert len(data['results']) == 3
    assert data['next_last_id'] is not None

    response2 = auth_client.get(
        REVIEW_COMMENTS_URL.format(review_id=review.pk) + f'?limit=3&last_id={data["next_last_id"]}'
    )
    data2 = response2.json()
    assert len(data2['results']) == 2
    assert data2['next_last_id'] is None


@pytest.mark.django_db
def test_edit_comment(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review, user=auth_client.user)
    response = auth_client.put(
        REVIEW_COMMENT_DETAIL_URL.format(review_id=review.pk, comment_id=comment.pk),
        data=json.dumps({'content': 'Updated content'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert response.json()['content'] == 'Updated content'
    comment.refresh_from_db()
    assert comment.content == 'Updated content'


@pytest.mark.django_db
def test_edit_comment_forbidden(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    response = auth_client.put(
        REVIEW_COMMENT_DETAIL_URL.format(review_id=review.pk, comment_id=comment.pk),
        data=json.dumps({'content': 'Updated content'}),
        content_type='application/json',
    )
    assert response.status_code == 403
    comment.refresh_from_db()
    assert comment.content != 'Updated content'


@pytest.mark.django_db
def test_delete_comment(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review, user=auth_client.user)
    response = auth_client.delete(
        REVIEW_COMMENT_DETAIL_URL.format(review_id=review.pk, comment_id=comment.pk)
    )
    assert response.status_code == 204
    comment.refresh_from_db()
    assert comment.deleted_at is not None
    assert not Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_get_review(review_factory, auth_client):
    review = review_factory(title='Amazing movie!', content='I loved it.', is_positive=True)
    response = auth_client.get(REVIEW_WRAPPER_URL.format(review_id=review.pk))
    assert response.status_code == 200
    assert response.json()['id'] == review.pk
    assert response.json()['title'] == 'Amazing movie!'
    assert response.json()['content'] == 'I loved it.'
    assert response.json()['is_positive'] is True


@pytest.mark.django_db
def test_delete_comment_forbidden(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    response = auth_client.delete(
        REVIEW_COMMENT_DETAIL_URL.format(review_id=review.pk, comment_id=comment.pk)
    )
    assert response.status_code == 403
    comment.refresh_from_db()
    assert comment.deleted_at is None


@pytest.mark.django_db
def test_delete_comment_cascades_replies(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review, user=auth_client.user)
    reply = comment_factory(review=review, reply_comment=comment)
    auth_client.delete(REVIEW_COMMENT_DETAIL_URL.format(review_id=review.pk, comment_id=comment.pk))
    reply.refresh_from_db()
    assert reply.deleted_at is not None


@pytest.mark.django_db
def test_delete_comment_cascades_reactions(
    review_factory, comment_factory, reaction_factory, auth_client
):
    review = review_factory()
    comment = comment_factory(review=review, user=auth_client.user)
    ct = ContentType.objects.get_for_model(Comment)
    reaction = reaction_factory(
        content_type=ct, object_id=comment.pk, emoji=Reaction.EmojiType.LIKE
    )
    auth_client.delete(REVIEW_COMMENT_DETAIL_URL.format(review_id=review.pk, comment_id=comment.pk))
    reaction.refresh_from_db()
    assert reaction.deleted_at is not None


# ===========================================================================
#  REPLIES
# ===========================================================================


@pytest.mark.django_db
def test_create_reply(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    response = auth_client.post(
        REVIEW_COMMENT_REPLIES_URL.format(review_id=review.pk, comment_id=comment.pk),
        data=json.dumps({'content': 'My reply'}),
        content_type='application/json',
    )
    assert response.status_code == 201
    assert response.json()['content'] == 'My reply'
    assert Comment.objects.filter(review=review, reply_comment=comment).count() == 1


@pytest.mark.django_db
def test_get_comment_replies(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    comment_factory(review=review, reply_comment=comment)
    comment_factory(review=review, reply_comment=comment)
    response = auth_client.get(
        REVIEW_COMMENT_REPLIES_URL.format(review_id=review.pk, comment_id=comment.pk)
    )
    assert response.status_code == 200
    assert len(response.json()['results']) == 2


@pytest.mark.django_db
def test_get_comment_replies_pagination(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    for _ in range(5):
        comment_factory(review=review, reply_comment=comment)
    response = auth_client.get(
        REVIEW_COMMENT_REPLIES_URL.format(review_id=review.pk, comment_id=comment.pk) + '?limit=3'
    )
    data = response.json()
    assert len(data['results']) == 3
    assert data['next_last_id'] is not None


# ===========================================================================
#  REACTIONS ON REVIEWS
# ===========================================================================


@pytest.mark.django_db
def test_add_review_reaction(review_factory, auth_client):
    review = review_factory()
    response = auth_client.post(
        REVIEW_REACTIONS_URL.format(review_id=review.pk),
        data=json.dumps({'emoji_code': 'LIKE'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert response.json()['id'] is not None
    ct = ContentType.objects.get_for_model(Review)
    assert Reaction.objects.filter(content_type=ct, object_id=review.pk).count() == 1


@pytest.mark.django_db
def test_add_review_reaction_duplicate(review_factory, reaction_factory, auth_client):
    review = review_factory()
    ct = ContentType.objects.get_for_model(Review)
    reaction_factory(
        user=auth_client.user,
        content_type=ct,
        object_id=review.pk,
        emoji=Reaction.EmojiType.LIKE,
    )
    response = auth_client.post(
        REVIEW_REACTIONS_URL.format(review_id=review.pk),
        data=json.dumps({'emoji_code': 'LIKE'}),
        content_type='application/json',
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_review_reactions(review_factory, reaction_factory, auth_client):
    review = review_factory()
    ct = ContentType.objects.get_for_model(Review)
    reaction_factory(content_type=ct, object_id=review.pk, emoji=Reaction.EmojiType.LIKE)
    reaction_factory(content_type=ct, object_id=review.pk, emoji=Reaction.EmojiType.LOVE)
    response = auth_client.get(REVIEW_REACTIONS_URL.format(review_id=review.pk))
    assert response.status_code == 200
    assert '👍' in response.json()['reactions']
    assert '❤️' in response.json()['reactions']


@pytest.mark.django_db
def test_delete_review_reaction(review_factory, reaction_factory, auth_client):
    review = review_factory()
    ct = ContentType.objects.get_for_model(Review)
    reaction = reaction_factory(
        user=auth_client.user,
        content_type=ct,
        object_id=review.pk,
        emoji=Reaction.EmojiType.LIKE,
    )
    response = auth_client.delete(
        REVIEW_REACTION_DETAIL_URL.format(review_id=review.pk, reaction_id=reaction.pk)
    )
    assert response.status_code == 204
    assert Reaction.objects.filter(pk=reaction.pk).exists() is False


@pytest.mark.django_db
def test_delete_review_reaction_forbidden(review_factory, reaction_factory, auth_client):
    review = review_factory()
    ct = ContentType.objects.get_for_model(Review)
    reaction = reaction_factory(content_type=ct, object_id=review.pk, emoji=Reaction.EmojiType.LIKE)
    response = auth_client.delete(
        REVIEW_REACTION_DETAIL_URL.format(review_id=review.pk, reaction_id=reaction.pk)
    )
    assert response.status_code == 403
    reaction.refresh_from_db()
    assert reaction.deleted_at is None


# ===========================================================================
#  REACTIONS ON COMMENTS
# ===========================================================================


@pytest.mark.django_db
def test_add_comment_reaction(review_factory, comment_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    response = auth_client.post(
        COMMENT_REACTIONS_URL.format(review_id=review.pk, comment_id=comment.pk),
        data=json.dumps({'emoji_code': 'LIKE'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert response.json()['id'] is not None


@pytest.mark.django_db
def test_add_comment_reaction_duplicate(
    review_factory, comment_factory, reaction_factory, auth_client
):
    review = review_factory()
    comment = comment_factory(review=review)
    ct = ContentType.objects.get_for_model(Comment)
    reaction_factory(
        user=auth_client.user,
        content_type=ct,
        object_id=comment.pk,
        emoji=Reaction.EmojiType.LIKE,
    )
    response = auth_client.post(
        COMMENT_REACTIONS_URL.format(review_id=review.pk, comment_id=comment.pk),
        data=json.dumps({'emoji_code': 'LIKE'}),
        content_type='application/json',
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_comment_reactions(review_factory, comment_factory, reaction_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    ct = ContentType.objects.get_for_model(Comment)
    reaction_factory(content_type=ct, object_id=comment.pk, emoji=Reaction.EmojiType.FIRE)
    response = auth_client.get(
        COMMENT_REACTIONS_URL.format(review_id=review.pk, comment_id=comment.pk)
    )
    assert response.status_code == 200
    assert '🔥' in response.json()['reactions']


@pytest.mark.django_db
def test_delete_comment_reaction(review_factory, comment_factory, reaction_factory, auth_client):
    review = review_factory()
    comment = comment_factory(review=review)
    ct = ContentType.objects.get_for_model(Comment)
    reaction = reaction_factory(
        user=auth_client.user,
        content_type=ct,
        object_id=comment.pk,
        emoji=Reaction.EmojiType.LIKE,
    )
    response = auth_client.delete(
        COMMENT_REACTION_DETAIL_URL.format(
            review_id=review.pk, comment_id=comment.pk, reaction_id=reaction.pk
        )
    )
    assert response.status_code == 204
    assert Reaction.objects.filter(pk=reaction.pk).exists() is False


@pytest.mark.django_db
def test_delete_comment_reaction_forbidden(
    review_factory, comment_factory, reaction_factory, auth_client
):
    review = review_factory()
    comment = comment_factory(review=review)
    ct = ContentType.objects.get_for_model(Comment)
    reaction = reaction_factory(
        content_type=ct, object_id=comment.pk, emoji=Reaction.EmojiType.LIKE
    )
    response = auth_client.delete(
        COMMENT_REACTION_DETAIL_URL.format(
            review_id=review.pk, comment_id=comment.pk, reaction_id=reaction.pk
        )
    )
    assert response.status_code == 403
    reaction.refresh_from_db()
    assert reaction.deleted_at is None


@pytest.mark.django_db
def test_get_review_translation(review_factory, auth_client, mock_reviews_deepl):
    review = review_factory(title='Great movie!', content='I really enjoyed it.', is_positive=True)

    def side_effect(text, target_lang):
        mock_result = MagicMock()
        if text == 'Great movie!':
            mock_result.text = '¡Gran película!'
        elif text == 'I really enjoyed it.':
            mock_result.text = 'Realmente lo disfruté.'
        return mock_result

    mock_reviews_deepl.translate_text.side_effect = side_effect

    response = auth_client.get(REVIEW_TRANSLATIONS_URL.format(review_id=review.pk))

    assert response.status_code == 200
    assert response.json()['title'] == '¡Gran película!'
    assert response.json()['content'] == 'Realmente lo disfruté.'


@pytest.mark.django_db
def test_get_comment_translation(review_factory, comment_factory, auth_client, mock_reviews_deepl):
    review = review_factory()
    comment = comment_factory(review=review, content='This is a comment.')

    def side_effect(text, target_lang):
        mock_result = MagicMock()
        if text == 'This is a comment.':
            mock_result.text = 'Este es un comentario.'
        return mock_result

    mock_reviews_deepl.translate_text.side_effect = side_effect

    response = auth_client.get(
        REVIEW_COMMENT_TRANSLATIONS_URL.format(review_id=review.pk, comment_id=comment.pk)
    )

    assert response.status_code == 200
    assert response.json()['content'] == 'Este es un comentario.'


def test_translate_success(mock_reviews_deepl):
    mock_reviews_deepl.translate_text.return_value = mock.MagicMock(text='Hola')
    assert __translate_text('Hello', 'es') == 'Hola'


def test_translate_authorization_error(mock_reviews_deepl):
    mock_reviews_deepl.translate_text.side_effect = deepl.AuthorizationException('error')
    assert __translate_text('Hello', 'es') == 'Hello'


def test_translate_deepl_error(mock_reviews_deepl):
    mock_reviews_deepl.translate_text.side_effect = deepl.DeepLException('error')
    assert __translate_text('Hello', 'es') == 'Hello'


def test_translate_connection_error(mock_reviews_deepl):
    mock_reviews_deepl.translate_text.side_effect = deepl.ConnectionException('error')
    assert __translate_text('Hello', 'es') == 'Hello'


def test_translate_quota_exceeded(mock_reviews_deepl):
    mock_reviews_deepl.translate_text.side_effect = deepl.QuotaExceededException('error')
    assert __translate_text('Hello', 'es') == 'Hello'


def test_translate_too_many_requests(mock_reviews_deepl):
    mock_reviews_deepl.translate_text.side_effect = deepl.TooManyRequestsException('error')
    assert __translate_text('Hello', 'es') == 'Hello'


def test_translate_unsupported_language(mock_reviews_deepl):
    assert __translate_text('Hello', 'jp') == 'Hello'


def test_translate_returns_list(mock_reviews_deepl):
    result = mock.MagicMock(text='Hola')
    mock_reviews_deepl.translate_text.return_value = [result]
    assert __translate_text('Hello', 'es') == 'Hola'
