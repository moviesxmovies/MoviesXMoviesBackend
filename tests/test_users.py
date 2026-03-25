import json
from datetime import datetime, timezone
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock, patch

import jwt
import pytest
import requests
from conftest import (
    FORGOT_PASSWORD_URL,
    LOGIN_URL,
    REFRESH_URL,
    RESEND_VERIFICATION_EMAIL_URL,
    SELF_USER_WRAPPER_URL,
    SIGNUP_URL,
    SUGGESTED_USERS_URL,
    TEST_USER_PASSWORD,
    TEST_USER_USERNAME,
    USER_DETAIL_URL,
    USER_FRIEND_REQUESTS_URL,
    USER_PREFERRED_LANGUAGE_URL,
    USER_REVIEWS_URL,
    VERIFY_USER_URL,
)
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import QuerySet
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from users.decorators import auth_required
from users.models import FriendRequest, FriendShip, User
from users.serializers import UserSerializer
from users.tasks import send_password_reset_email, send_verification_email

# =================================================================
# AUTH
# =================================================================


@pytest.mark.django_db
def test_login_success(client, create_test_user):
    data = {
        'username': TEST_USER_USERNAME,
        'password': TEST_USER_PASSWORD,
    }
    response = client.post(LOGIN_URL, data)
    assert response.status_code == 200
    assert 'access' in response.json()
    assert 'refresh' in response.json()


@pytest.mark.django_db
def test_login_user_not_exist(client):
    data = {
        'username': 'invalid_user',
        'password': 'invalid_pass',
    }
    response = client.post(LOGIN_URL, data)
    assert response.status_code == 401
    assert 'access' not in response.json()
    assert 'refresh' not in response.json()


@pytest.mark.django_db
def test_login_missing_body(client):
    response = client.post(LOGIN_URL)
    assert response.status_code == 400
    assert 'access' not in response.json()
    assert 'refresh' not in response.json()


@pytest.mark.django_db
def test_login_missing_required_fields(client):
    data = {
        'username': TEST_USER_USERNAME,
    }
    response = client.post(LOGIN_URL, data)
    assert response.status_code == 400
    assert 'access' not in response.json()
    assert 'refresh' not in response.json()


@pytest.mark.django_db
def test_token_refresh_success(client, create_test_user):
    # Get login tokens first
    login_data = {
        'username': TEST_USER_USERNAME,
        'password': TEST_USER_PASSWORD,
    }
    login_response = client.post(LOGIN_URL, login_data)
    assert login_response.status_code == 200
    refresh_token = login_response.json().get('refresh')
    assert refresh_token is not None

    # Now refresh the token
    refresh_data = {
        'refresh': refresh_token,
    }
    refresh_response = client.post(REFRESH_URL, refresh_data)
    assert refresh_response.status_code == 200
    assert 'access' in refresh_response.json()


@pytest.mark.django_db
def test_token_refresh_invalid_token(client):
    refresh_data = {
        'refresh': 'invalid_token',
    }
    refresh_response = client.post(REFRESH_URL, refresh_data)
    assert refresh_response.status_code == 401
    assert 'access' not in refresh_response.json()


@pytest.mark.django_db
def test_token_refresh_missing_body(client):
    refresh_response = client.post(REFRESH_URL)
    assert refresh_response.status_code == 400
    assert 'access' not in refresh_response.json()


@pytest.mark.django_db
def test_token_refresh_missing_required_fields(client):
    refresh_data = {'invalid_field': 'some_value'}
    refresh_response = client.post(REFRESH_URL, refresh_data)
    assert refresh_response.status_code == 400
    assert 'access' not in refresh_response.json()


@pytest.mark.django_db
def test_obtain_token_contains_custom_claims(client, create_test_user):
    data = {
        'username': TEST_USER_USERNAME,
        'password': TEST_USER_PASSWORD,
    }
    response = client.post(LOGIN_URL, data)
    assert response.status_code == 200
    access_token = response.json().get('access')
    assert access_token is not None

    try:
        token = UntypedToken(access_token)
        assert token['username'] == TEST_USER_USERNAME
        assert token['boarded'] is False
        assert token['verified'] is False
    except (InvalidToken, TokenError) as e:
        pytest.fail(f'Token validation failed: {e}')


@pytest.mark.django_db
def test_refresh_token_contains_custom_claims(client, create_test_user):
    # Get login tokens first
    login_data = {
        'username': TEST_USER_USERNAME,
        'password': TEST_USER_PASSWORD,
    }
    login_response = client.post(LOGIN_URL, login_data)
    assert login_response.status_code == 200
    refresh_token = login_response.json().get('refresh')
    assert refresh_token is not None

    # Now refresh the token
    refresh_data = {
        'refresh': refresh_token,
    }
    refresh_response = client.post(REFRESH_URL, refresh_data)
    assert refresh_response.status_code == 200
    access_token = refresh_response.json().get('access')
    assert access_token is not None

    try:
        token = UntypedToken(access_token)
        assert token['username'] == TEST_USER_USERNAME
        assert token['boarded'] is False
        assert token['verified'] is False
    except (InvalidToken, TokenError) as e:
        pytest.fail(f'Token validation failed: {e}')


# =================================================================
# USER MODEL
# =================================================================


@pytest.mark.django_db
def test_user_following_person_extracted(user_factory, person_factory):
    persona = person_factory()

    user = user_factory(following_person=[persona])

    assert persona in user.following_person.all()


@pytest.mark.django_db
def test_user_platforms_extracted(user_factory, platform_factory):
    netflix = platform_factory(name='Netflix')

    user = user_factory(platforms=[netflix])

    assert netflix in user.platforms.all()


def test_user_factory_build(user_factory):
    user = user_factory.build()
    assert user.pk is None


@pytest.mark.django_db
def test_user_is_friend_self(user_factory):
    user1 = user_factory()

    assert not user1.is_friend(user1)


@pytest.mark.django_db
def test_user_is_friend_null(user_factory):
    user1 = user_factory()

    assert not user1.is_friend(None)


@pytest.mark.django_db
def test_suggest_friends_logic():
    me = User.objects.create_user(username='me', email='me@test.com')

    santi = User.objects.create_user(username='santi', email='santi@test.com')
    elena = User.objects.create_user(username='elena', email='elena@test.com')
    FriendShip.objects.create(user1=me, user2=santi)

    pedro = User.objects.create_user(username='pedro', email='pedro@test.com')
    FriendShip.objects.create(user1=elena, user2=pedro)
    FriendShip.objects.create(user1=santi, user2=pedro)

    maria = User.objects.create_user(username='maria', email='maria@test.com')
    FriendShip.objects.create(user1=santi, user2=maria)

    juan = User.objects.create_user(username='juan', email='juan@test.com')
    FriendShip.objects.create(user1=me, user2=juan)
    FriendShip.objects.create(user1=juan, user2=pedro)

    suggestions = me.suggest_friends()

    assert isinstance(suggestions, QuerySet)

    assert me not in suggestions, 'Should not suggest self'
    assert juan not in suggestions, 'Should not suggest already followed users'

    pedro_sugg = suggestions.get(username='pedro')
    maria_sugg = suggestions.get(username='maria')
    assert pedro_sugg.common_friends_count == 2, 'Pedro should have 2 common friends'
    assert maria_sugg.common_friends_count == 1, 'María should have 1 common friend'

    assert suggestions[0] == pedro, 'Pedro should be first (most common friends)'
    assert suggestions[1] == maria, 'María should be second (fewer common friends)'

    assert suggestions.count() == 2, 'Should have exactly 2 unique suggestions'


@pytest.mark.django_db
def test_gest_user_friends(user_factory):
    user1 = user_factory(username='user1')
    user2 = user_factory(username='user2')
    user3 = user_factory(username='user3')

    FriendShip.objects.create(user1=user1, user2=user2)
    FriendShip.objects.create(user1=user1, user2=user3)

    friends_of_user1 = user1.get_friends()
    assert set(friends_of_user1) == {user2, user3}


# ==========================================================================
# FRIENDREQUEST MODEL
# ==========================================================================


@pytest.mark.django_db
def test_friend_request_str(friend_request_factory):
    friend_request = friend_request_factory()
    expected_str = f'FriendRequest from {friend_request.from_user.username} to {friend_request.to_user.username}'
    assert str(friend_request) == expected_str


@pytest.mark.django_db
def test_friend_request_accept(friend_request_factory):
    friend_request = friend_request_factory(status=FriendRequest.Status.PENDING)

    friend_request.accept()

    assert friend_request.status == FriendRequest.Status.ACCEPTED, (
        'Friend request status should be ACCEPTED'
    )


@pytest.mark.django_db
def test_friend_request_reject(friend_request_factory):
    friend_request = friend_request_factory(status=FriendRequest.Status.PENDING)

    friend_request.reject()

    assert friend_request.status == FriendRequest.Status.REJECTED, (
        'Friend request status should be REJECTED'
    )


# ===========================================================================
# SERIALIZERS
# ===========================================================================
@pytest.mark.django_db
def test_user_serializer(user_factory):
    user = user_factory()
    serialized = UserSerializer(user).serialize()

    assert serialized['id'] == user.pk
    assert serialized['username'] == user.username
    assert serialized['bio'] == user.bio
    assert not serialized['is_friend']


@pytest.mark.django_db
def test_user_serializer_is_following(user_factory):
    user = user_factory()
    user_request = user_factory()
    FriendShip.objects.create(user1=user_request, user2=user)
    user_request.save()
    request = SimpleNamespace(
        user=user_request, build_absolute_uri=lambda x: f'http://testserver{x}'
    )
    serialized = UserSerializer(user, request=request).serialize()

    assert serialized['id'] == user.pk
    assert serialized['username'] == user.username
    assert serialized['bio'] == user.bio
    assert serialized['is_friend']


# ===========================================================================
# DECORATORS
# ===========================================================================
@pytest.fixture
def mock_view_auth_required():

    @auth_required
    def view(request):
        return JsonResponse(
            {'username': request.user.username, 'user_id': request.user.id},
            status=HTTPStatus.OK,
        )

    return view


@pytest.mark.django_db
def test_auth_success(rf, user_factory, generate_jwt, mock_view_auth_required):
    user = user_factory(verified=True)
    token = generate_jwt(user)

    request = rf.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
    response = mock_view_auth_required(request)

    data = json.loads(response.content)
    assert response.status_code == HTTPStatus.OK
    assert data['user_id'] == user.id
    assert data['username'] == user.username


@pytest.mark.django_db
def test_auth_no_token_provided(rf, mock_view_auth_required):
    request = rf.get('/')
    response = mock_view_auth_required(request)

    data = json.loads(response.content)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert data['error'] == 'You need to be authenticated'


@pytest.mark.django_db
def test_auth_invalid_token_type(rf, user_factory, mock_view_auth_required):
    user = user_factory()
    payload = {'user_id': user.id, 'token_type': 'refresh'}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    request = rf.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
    response = mock_view_auth_required(request)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content)['error'] == 'Token type is invalid'


@pytest.mark.django_db
def test_auth_expired_token(rf, user_factory, mock_view_auth_required):
    user = user_factory()
    from datetime import datetime, timedelta

    payload = {
        'user_id': user.id,
        'token_type': 'access',
        'exp': datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    request = rf.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
    response = mock_view_auth_required(request)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'expired' in json.loads(response.content)['error'].lower()


@pytest.mark.django_db
def test_auth_user_not_exists(rf, user_factory, generate_jwt, mock_view_auth_required):
    user = user_factory()
    token = generate_jwt(user)
    user.delete()

    request = rf.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
    response = mock_view_auth_required(request)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert json.loads(response.content)['error'] == 'Token is invalid'


@pytest.mark.django_db
def test_auth_malformed_token(rf, mock_view_auth_required):
    malformed_token = 'this.is.not.a.valid.token'
    request = rf.get('/', HTTP_AUTHORIZATION=f'Bearer {malformed_token}')
    response = mock_view_auth_required(request)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content)['error'] == 'Token is invalid or has incorrect padding'


# =================================================================
# TASKS
# =================================================================
@pytest.mark.django_db
def test_send_verification_email_logic(user_factory):
    user = user_factory(username='testuser', email='test@example.com')

    send_verification_email(user)

    user.refresh_from_db()
    assert user.verification_code is not None
    assert 0 <= int(user.verification_code) <= 999999

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.subject == f'Verification of MoviesXMovies account for {user.username}'
    assert sent_email.to == [user.email]
    assert sent_email.content_subtype == 'html'

    expected_html = render_to_string('users/email/verification-email.html', {'user': user})
    assert sent_email.body == expected_html


@pytest.mark.django_db
def test_send_password_reset_email_logic(user_factory):
    user = user_factory(username='testuser', email='test@example.com')

    send_password_reset_email(user)

    user.refresh_from_db()
    assert user.forgot_password_code is not None
    assert 0 <= int(user.forgot_password_code) <= 999999

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]

    assert sent_email.subject == f'Password reset for MoviesXMovies account of {user.username}'
    assert sent_email.to == [user.email]
    assert sent_email.content_subtype == 'html'

    expected_html = render_to_string('users/email/password-reset-email.html', {'user': user})
    assert sent_email.body == expected_html


# =================================================================
# VIEWS
# =================================================================
@pytest.mark.django_db
def test_verify_user_success(auth_client):
    auth_client.user.verification_code = '000321'
    auth_client.user.verified = False
    auth_client.user.save()

    payload = {'verification_code': '000321'}

    url = VERIFY_USER_URL
    response = auth_client.post(url, data=payload, content_type='application/json')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] is True

    auth_client.user.refresh_from_db()
    assert auth_client.user.verified is True


@pytest.mark.django_db
def test_verify_user_already_verified(auth_client):
    auth_client.user.verification_code = '000321'
    auth_client.user.verified = True
    auth_client.user.save()

    payload = {'verification_code': '000321'}

    url = VERIFY_USER_URL
    response = auth_client.post(url, data=payload, content_type='application/json')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] is True

    auth_client.user.refresh_from_db()
    assert auth_client.user.verified is True


@pytest.mark.django_db
def test_verify_user_incorrect_code(auth_client):
    auth_client.user.verification_code = '000321'
    auth_client.user.verified = False
    auth_client.user.save()

    payload = {'verification_code': '123456'}

    url = VERIFY_USER_URL
    response = auth_client.post(url, data=payload, content_type='application/json')

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == 'Verification code is incorrect'

    auth_client.user.refresh_from_db()
    assert auth_client.user.verified is False


@pytest.mark.django_db
def test_resend_verification_email_success_cooldown(auth_client):
    url = RESEND_VERIFICATION_EMAIL_URL
    auth_client.user.verified = False
    auth_client.user.save()

    if not hasattr(cache, 'ttl'):
        cache.ttl = lambda x: 0

    with mock.patch.object(cache, 'ttl', side_effect=[0, 60]):
        response1 = auth_client.post(url)
        assert response1.status_code == HTTPStatus.OK

        response2 = auth_client.post(url)
        assert response2.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert 'You can resend the verification email in' in response2.json()['error']


@pytest.mark.django_db
def test_resend_verification_email_already_verified(auth_client):
    url = RESEND_VERIFICATION_EMAIL_URL
    auth_client.user.verified = True
    auth_client.user.save()

    response = auth_client.post(url)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] == 'User is already verified'


@pytest.mark.django_db
def test_suggest_friends_empty(auth_client):
    url = SUGGESTED_USERS_URL
    response = auth_client.get(url)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['count'] == 0
    assert response.json()['results'] == []
    assert response.json()['current_page'] == 1
    assert response.json()['total_pages'] == 1
    assert not response.json()['has_next']
    assert not response.json()['has_previous']


@pytest.mark.django_db
def test_suggest_friends_with_suggestions(auth_client, user_factory):
    user1 = user_factory(username='user1')
    user2 = user_factory(username='user2')
    user3 = user_factory(username='user3')

    FriendShip.objects.create(user1=auth_client.user, user2=user1)
    FriendShip.objects.create(user1=auth_client.user, user2=user2)

    FriendShip.objects.create(user1=user1, user2=user3)
    FriendShip.objects.create(user1=user2, user2=user3)

    url = SUGGESTED_USERS_URL
    response = auth_client.get(url)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['count'] == 1
    assert response.json()['results'][0]['username'] == 'user3'
    assert response.json()['current_page'] == 1
    assert response.json()['total_pages'] == 1
    assert not response.json()['has_next']
    assert not response.json()['has_previous']


@pytest.mark.django_db
def test_suggest_friends_pagination(auth_client, user_factory):
    targets = [user_factory(username=f'target{i}') for i in range(15)]

    for i in range(5):
        bridge_user = user_factory(username=f'bridge{i}')
        for target in targets:
            FriendShip.objects.create(user1=bridge_user, user2=target)
        FriendShip.objects.create(user1=auth_client.user, user2=bridge_user)

    url = f'{SUGGESTED_USERS_URL}?page=2&limit=5'
    response = auth_client.get(url)

    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert data['count'] == 15
    assert len(data['results']) == 5
    assert data['current_page'] == 2
    assert data['total_pages'] == 3
    assert data['has_next']
    assert data['has_previous']
    assert data['results'][0]['username'] == 'target5'


@pytest.mark.django_db
def test_self_user_detail(auth_client):
    response = auth_client.get(SELF_USER_WRAPPER_URL)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['username'] == auth_client.user.username
    assert data['id'] == auth_client.user.id


@pytest.mark.django_db
def test_user_detail(auth_client, user_factory):
    user = user_factory(username='otheruser')
    response = auth_client.get(USER_DETAIL_URL.format(username=user.username))
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['username'] == user.username
    assert data['id'] == user.id


@pytest.mark.django_db
def test_user_signup(auth_client):
    payload = {
        'email': 'test@example.com',
        'username': 'test',
        'first_name': 'test',
        'last_name': 'test',
        'password': 'testpassword',
    }

    response = auth_client.post(SIGNUP_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == 2
    assert response.json()['username'] == 'test'


@pytest.mark.django_db
def test_user_signup_with_picture(auth_client):
    picture_file = SimpleUploadedFile(
        name='test_picture.jpg',
        content=b'Test picture content',
        content_type='image/jpeg',
    )
    payload = {
        'email': 'test@example.com',
        'username': 'test',
        'first_name': 'test',
        'last_name': 'test',
        'password': 'testpassword',
        'picture': picture_file,
    }
    response = auth_client.post(SIGNUP_URL, data=payload, content_type=MULTIPART_CONTENT)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['username'] == 'test'
    (response.json())
    assert response.json()['picture'].startswith('http://testserver/media/users/user_test_profile_')
    assert response.json()['picture'].endswith('.jpg')


@pytest.mark.django_db
def test_user_signup_exception(auth_client):
    payload = {
        'email': 'testexample.com',
        'username': 'test',
        'first_name': 'test',
        'last_name': 'test',
        'password': 'testpassword',
    }

    response = auth_client.post(SIGNUP_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['email'] == ['Enter a valid email address.']


@pytest.mark.django_db
def test_user_signup_duplicate_email(auth_client, user_factory):
    existing_user = user_factory(
        email='test@example.com',
        username='existinguser',
        first_name='Existing',
        last_name='User',
    )

    payload = {
        'email': existing_user.email,
        'username': 'newuser',
        'first_name': 'New',
        'last_name': 'User',
        'password': 'testpassword',
    }

    response = auth_client.post(SIGNUP_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['email'] == ['User with this Email already exists.']


@pytest.mark.django_db
def test_user_signup_invalid_password(auth_client):
    payload = {
        'email': 'test@example.com',
        'username': 'test',
        'first_name': 'test',
        'last_name': 'test',
        'password': '123456789',  # Invalid: too short , only numeric, and common
    }

    response = auth_client.post(SIGNUP_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == [
        'This password is too short. It must contain at least 10 characters.',
        'This password is too common.',
        'This password is entirely numeric.',
    ]


@pytest.mark.django_db
def test_user_reviews(auth_client, user_factory, review_factory, movie_factory):
    user = user_factory(username='reviewer')

    movie1 = movie_factory(title='Movie 1')
    movie2 = movie_factory(title='Movie 2')

    review1 = review_factory(user=user, movie=movie1)
    review2 = review_factory(user=user, movie=movie2)

    response = auth_client.get(USER_REVIEWS_URL.format(username=user.username))
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['count'] == 2
    assert 'results' in data

    review_ids = {review['id'] for review in data['results']}
    assert review1.id in review_ids
    assert review2.id in review_ids


@pytest.mark.django_db
def test_edit_user(auth_client):
    payload = {
        'bio': 'This is my new bio',
    }

    response = auth_client.put(SELF_USER_WRAPPER_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['bio'] == 'This is my new bio'

    auth_client.user.refresh_from_db()
    assert auth_client.user.bio == 'This is my new bio'


@pytest.mark.django_db
def test_edit_user_with_picture(auth_client):
    picture_file = SimpleUploadedFile(
        name='test_picture.jpg',
        content=b'Test picture content',
        content_type='image/jpeg',
    )
    payload = {
        'bio': 'This is my new bio with picture',
        'picture': picture_file,
    }
    response = auth_client.put(
        SELF_USER_WRAPPER_URL,
        data=encode_multipart(BOUNDARY, payload),
        content_type=MULTIPART_CONTENT,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['bio'] == 'This is my new bio with picture'
    auth_client.user.refresh_from_db()
    assert auth_client.user.bio == 'This is my new bio with picture'
    assert auth_client.user.picture.name.startswith(
        f'users/user_{auth_client.user.username}_profile_'
    )
    assert auth_client.user.picture.name.endswith('.jpg')


@pytest.mark.django_db
def test_edit_user_invalid_field(auth_client):
    payload = {
        'invalid_field': 'This field does not exist',
    }

    response = auth_client.put(SELF_USER_WRAPPER_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK
    assert response.json().get('invalid_field') is None


@pytest.mark.django_db
def test_edit_user_empty_field(auth_client):
    auth_client.user.bio = 'Existing bio'
    auth_client.user.save()
    payload = {
        'bio': '',
    }

    response = auth_client.put(SELF_USER_WRAPPER_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['bio'] == 'Existing bio'


@pytest.mark.django_db
def test_edit_user_invalid_password(auth_client):
    payload = {
        'password': '123456789',  # Invalid: too short , only numeric, and common
    }

    response = auth_client.put(SELF_USER_WRAPPER_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == [
        'This password is too short. It must contain at least 10 characters.',
        'This password is too common.',
        'This password is entirely numeric.',
    ]


@pytest.mark.django_db
def test_edit_user_password_success(auth_client):
    payload = {
        'password': 'NewStrongPassword123',
    }

    response = auth_client.put(SELF_USER_WRAPPER_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK

    auth_client.user.refresh_from_db()
    assert auth_client.user.check_password('NewStrongPassword123')


@pytest.mark.django_db
def test_edit_user_email_change(auth_client):
    payload = {
        'email': 'new_email@mail.com',
    }

    response = auth_client.put(SELF_USER_WRAPPER_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK

    auth_client.user.refresh_from_db()
    assert auth_client.user.email == 'new_email@mail.com'
    assert auth_client.user.verified is False


@pytest.mark.django_db
def test_forgot_password(client, user_factory):
    user = user_factory(email='testuser@mail.com')
    response = client.get(
        FORGOT_PASSWORD_URL + '?email=' + user.email,
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] == 'Password reset email sent'


@pytest.mark.django_db
def test_forgot_password_nonexistent_email(client):
    response = client.get(
        FORGOT_PASSWORD_URL + '?email=' + 'nonexistent@mail.com',
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['error'] == 'User not found'


@pytest.mark.django_db
def test_forgot_password_validation(client, user_factory):
    user = user_factory(email='testuser@mail.com', forgot_password_code='valid_code')
    response = client.post(
        FORGOT_PASSWORD_URL,
        data={
            'forgot_password_code': 'valid_code',
            'new_password': 'NewPassword123',
            'email': user.email,
        },
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] == 'Password reset successful'


@pytest.mark.django_db
def test_forgot_password_validation_invalid_code(client, user_factory):
    user = user_factory(email='testuser@mail.com', forgot_password_code='valid_code')
    response = client.post(
        FORGOT_PASSWORD_URL,
        data={
            'forgot_password_code': 'invalid_code',
            'new_password': 'NewPassword123',
            'email': user.email,
        },
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == 'Invalid verification code'


@pytest.mark.django_db
def test_forgot_password_validation_nonexistent_email(client):
    response = client.post(
        FORGOT_PASSWORD_URL,
        data={
            'forgot_password_code': 'some_code',
            'new_password': 'NewPassword123',
            'email': 'nonexistent@mail.com',
        },
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == 'Invalid verification code'


@pytest.mark.django_db
def test_forgot_password_validation_weak_password(client, user_factory):
    user = user_factory(email='testuser@mail.com', forgot_password_code='valid_code')
    response = client.post(
        FORGOT_PASSWORD_URL,
        data={
            'forgot_password_code': 'valid_code',
            'new_password': 'weak',
            'email': user.email,
        },
        content_type='application/json',
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == [
        'This password is too short. It must contain at least 10 characters.'
    ]


@pytest.mark.django_db
def test_set_preferred_language(auth_client):
    payload = {
        'preferred_language': 'es',
    }

    response = auth_client.post(
        USER_PREFERRED_LANGUAGE_URL, data=payload, content_type='application/json'
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] is True

    auth_client.user.refresh_from_db()
    assert auth_client.user.preferred_language == 'es'


@pytest.mark.django_db
def test_set_preferred_language_invalid_code(auth_client):
    payload = {
        'preferred_language': 'invalid_code',
    }

    response = auth_client.post(
        USER_PREFERRED_LANGUAGE_URL, data=payload, content_type='application/json'
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['error'] == 'Invalid language code'

    auth_client.user.refresh_from_db()
    assert auth_client.user.preferred_language != 'invalid_code'


@pytest.mark.django_db
def test_get_preferred_language(auth_client):
    auth_client.user.preferred_language = 'fr'
    auth_client.user.save()
    response = auth_client.get(USER_PREFERRED_LANGUAGE_URL)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['preferred_language'] == auth_client.user.preferred_language


# =================================================================
# ADAPTERS
# =================================================================

# =================================================================
# Stubs
# =================================================================


class FakeUser:
    def __init__(self, pk=1, email='user@example.com', picture_name='users/default.png'):
        self.pk = pk
        self.email = email
        self.picture = MagicMock()
        self.picture.name = picture_name
        self.username = f'user{pk}'

    def save(self, *args, **kwargs):
        return self


class FakeSocialLogin:
    def __init__(self, user=None, is_existing=False, extra_data=None):
        self.user = user or FakeUser()
        self.is_existing = is_existing
        self.account = MagicMock()
        self.account.extra_data = extra_data or {}
        self.connect = MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    from users.adapters import SocialAccountAdapter

    instance = SocialAccountAdapter.__new__(SocialAccountAdapter)

    with patch.object(SocialAccountAdapter.__bases__[0], 'save_user') as mock_super_save:
        instance._mock_super_save = mock_super_save
        yield instance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_sl(picture_url=None, user_picture_name='users/default.png'):
    user = FakeUser(picture_name=user_picture_name)
    extra_data = {'picture': picture_url} if picture_url else {}
    return FakeSocialLogin(user=user, extra_data=extra_data), user


# ---------------------------------------------------------------------------
# pre_social_login tests
# ---------------------------------------------------------------------------


class TestPreSocialLogin:
    def test_returns_early_when_login_already_exists(self, adapter):
        """No DB look-up or connect() call for an existing social login."""
        sl = FakeSocialLogin(is_existing=True)

        with patch('users.adapters.User') as MockUser:
            adapter.pre_social_login(request=MagicMock(), sociallogin=sl)

        MockUser.objects.get.assert_not_called()
        sl.connect.assert_not_called()

    def test_returns_early_when_email_is_missing(self, adapter):
        """No DB look-up when the OAuth provider returns no e-mail."""
        sl = FakeSocialLogin(user=FakeUser(email=''), is_existing=False)

        with patch('users.adapters.User') as MockUser:
            adapter.pre_social_login(request=MagicMock(), sociallogin=sl)

        MockUser.objects.get.assert_not_called()
        sl.connect.assert_not_called()

    def test_connects_to_existing_user_with_matching_email(self, adapter):
        """When a local account with the same e-mail exists, connect() is called."""
        existing = FakeUser(pk=99, email='match@example.com')
        sl = FakeSocialLogin(user=FakeUser(email='match@example.com'), is_existing=False)
        request = MagicMock()

        with patch('users.adapters.User') as MockUser:
            MockUser.objects.get.return_value = existing
            adapter.pre_social_login(request=request, sociallogin=sl)

        MockUser.objects.get.assert_called_once_with(email='match@example.com')
        sl.connect.assert_called_once_with(request, existing)

    def test_does_not_connect_when_email_not_found(self, adapter):
        """User.DoesNotExist is swallowed silently; connect() is never called."""
        sl = FakeSocialLogin(user=FakeUser(email='new@example.com'), is_existing=False)

        with patch('users.adapters.User') as MockUser:
            MockUser.DoesNotExist = LookupError
            MockUser.objects.get.side_effect = LookupError
            adapter.pre_social_login(request=MagicMock(), sociallogin=sl)

        sl.connect.assert_not_called()


# ---------------------------------------------------------------------------
# save_user tests
#
# Condition: if picture_url and user.picture.name.endswith('users/default.png')
# → picture is downloaded only for users who still have the default picture.
# → users with a custom picture are skipped.
# ---------------------------------------------------------------------------


class TestSaveUser:
    def test_returns_user_from_super(self, adapter):
        """save_user always returns the user produced by the parent method."""
        sl, user = make_sl()
        adapter._mock_super_save.return_value = user

        result = adapter.save_user(MagicMock(), sl)

        assert result is user

    def test_saves_profile_picture_for_new_user_with_default_picture(self, adapter):
        """Happy path: URL present + user has default picture → picture downloaded."""
        sl, user = make_sl(
            picture_url='https://example.com/photo.jpg',
            user_picture_name='users/default.png',
        )
        adapter._mock_super_save.return_value = user

        fake_response = MagicMock(status_code=200, content=b'JPEG_BYTES')

        with patch('requests.get', return_value=fake_response) as mock_get:
            adapter.save_user(MagicMock(), sl)

        mock_get.assert_called_once_with('https://example.com/photo.jpg', timeout=5)
        user.picture.save.assert_called_once()
        assert (
            user.picture.save.call_args[0][0]
            == f'profile_{user.username}_OAUTH_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
        )

    def test_skips_picture_when_user_already_has_custom_picture(self, adapter):
        """User with a non-default picture is not overwritten."""
        sl, user = make_sl(
            picture_url='https://example.com/photo.jpg',
            user_picture_name='users/custom_avatar.png',
        )
        adapter._mock_super_save.return_value = user

        with patch('requests.get') as mock_get:
            adapter.save_user(MagicMock(), sl)

        mock_get.assert_not_called()
        user.picture.save.assert_not_called()

    def test_skips_picture_when_url_absent(self, adapter):
        """No HTTP request when extra_data has no 'picture' key."""
        sl, user = make_sl(picture_url=None)
        adapter._mock_super_save.return_value = user

        with patch('requests.get') as mock_get:
            adapter.save_user(MagicMock(), sl)

        mock_get.assert_not_called()
        user.picture.save.assert_not_called()

    def test_skips_picture_on_failed_http_response(self, adapter):
        sl, user = make_sl(
            picture_url='https://example.com/photo.jpg',
            user_picture_name='users/default.png',
        )
        adapter._mock_super_save.return_value = user

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError('404')

        with patch('requests.get', return_value=mock_response):
            adapter.save_user(MagicMock(), sl)

        user.picture.save.assert_not_called()

    def test_swallows_request_exception(self, adapter):
        """A network error must not propagate; save_user still returns the user."""
        import requests as req

        sl, user = make_sl(
            picture_url='https://example.com/photo.jpg',
            user_picture_name='users/default.png',
        )
        adapter._mock_super_save.return_value = user

        with patch('requests.get', side_effect=req.RequestException('timeout')):
            result = adapter.save_user(MagicMock(), sl)

        assert result is user
        user.picture.save.assert_not_called()

    def test_picture_file_content_is_correct(self, adapter):
        """The bytes from the response are wrapped in BytesIO then File before saving."""
        sl, user = make_sl(
            picture_url='https://example.com/photo.jpg',
            user_picture_name='users/default.png',
        )
        adapter._mock_super_save.return_value = user

        image_bytes = b'\xff\xd8\xff\xe0JPEG'
        fake_response = MagicMock(status_code=200, content=image_bytes)

        with (
            patch('requests.get', return_value=fake_response),
            patch('users.adapters.File') as MockFile,
            patch('users.adapters.BytesIO') as MockBytesIO,
        ):
            adapter.save_user(MagicMock(), sl)

        MockBytesIO.assert_called_once_with(image_bytes)
        MockFile.assert_called_once_with(MockBytesIO.return_value)


@pytest.mark.django_db
class TestFriendRequest:
    def test_send_friend_request(
        self,
        auth_client,
        user_factory,
    ):
        sender = auth_client.user
        receiver = user_factory()

        response = auth_client.post(USER_FRIEND_REQUESTS_URL.format(username=receiver.username))
        assert response.status_code == HTTPStatus.OK
        assert response.json()['status'] == 'Friend request sent'
        assert FriendRequest.objects.filter(from_user=sender, to_user=receiver).exists()

    def test_send_friend_request_to_self(self, auth_client):
        response = auth_client.post(
            USER_FRIEND_REQUESTS_URL.format(username=auth_client.user.username)
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()['status'] == 'You cannot friend yourself'

    def test_send_duplicate_friend_request(self, auth_client, user_factory):
        sender = auth_client.user
        receiver = user_factory()

        FriendRequest.objects.create(from_user=sender, to_user=receiver)

        response = auth_client.post(USER_FRIEND_REQUESTS_URL.format(username=receiver.username))
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()['status'] == 'Friend request already sent'

    def test_send_friend_request_to_existing_friend(self, auth_client, user_factory):
        sender = auth_client.user
        receiver = user_factory()

        FriendShip.objects.create(user1=sender, user2=receiver)

        response = auth_client.post(USER_FRIEND_REQUESTS_URL.format(username=receiver.username))
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()['status'] == 'Already friends'

    def test_accept_friend_request(self, auth_client, user_factory):
        sender = user_factory()
        receiver = auth_client.user

        friend_request = FriendRequest.objects.create(from_user=sender, to_user=receiver)

        response = auth_client.post(
            USER_FRIEND_REQUESTS_URL.format(username=sender.username),
            data={'action': 'accept'},
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()['status'] == 'Friend request accepted'
        friend_request.refresh_from_db()
        assert friend_request.status == FriendRequest.Status.ACCEPTED
        assert (
            FriendShip.objects.filter(user1=sender, user2=receiver).exists()
            or FriendShip.objects.filter(user1=receiver, user2=sender).exists()
        )

    def test_reject_friend_request(self, auth_client, user_factory):
        sender = user_factory()
        receiver = auth_client.user

        friend_request = FriendRequest.objects.create(from_user=sender, to_user=receiver)

        response = auth_client.delete(
            USER_FRIEND_REQUESTS_URL.format(username=sender.username),
            data={'action': 'reject'},
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()['status'] == 'Friend request rejected'
        friend_request.refresh_from_db()
        assert friend_request.status == FriendRequest.Status.REJECTED
        assert (
            not FriendShip.objects.filter(user1=sender, user2=receiver).exists()
            and not FriendShip.objects.filter(user1=receiver, user2=sender).exists()
        )

    def test_reject_nonexistent_friend_request(self, auth_client, user_factory):
        sender = user_factory()
        receiver = auth_client.user

        response = auth_client.delete(
            USER_FRIEND_REQUESTS_URL.format(username=sender.username),
            data={'action': 'reject'},
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()['status'] == 'No friend relationship to reject'

    def test_reject_self_friend_request(self, auth_client):
        response = auth_client.delete(
            USER_FRIEND_REQUESTS_URL.format(username=auth_client.user.username),
            data={'action': 'reject'},
            content_type='application/json',
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()['status'] == 'You cannot unfriend yourself'

    def test_send_friend_request_after_rejection(self, auth_client, user_factory):
        sender = auth_client.user
        receiver = user_factory()

        friend_request = FriendRequest.objects.create(from_user=sender, to_user=receiver)
        friend_request.status = FriendRequest.Status.REJECTED
        friend_request.save()

        response = auth_client.post(USER_FRIEND_REQUESTS_URL.format(username=receiver.username))
        assert response.status_code == HTTPStatus.OK
        assert response.json()['status'] == 'Friend request sent'
        friend_request.refresh_from_db()
        assert friend_request.status == FriendRequest.Status.PENDING
