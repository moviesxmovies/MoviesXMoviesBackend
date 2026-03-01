import json
from datetime import timezone
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

import jwt
import pytest
from conftest import (
    LOGIN_URL,
    REFRESH_URL,
    RESEND_VERIFICATION_EMAIL_URL,
    SELF_USER_DETAIL_URL,
    SIGNUP_URL,
    SUGGESTED_USERS_URL,
    TEST_USER_PASSWORD,
    TEST_USER_USERNAME,
    USER_DETAIL_URL,
    USER_REVIEWS_URL,
    VERIFY_USER_URL,
)
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.db.models import QuerySet
from django.http import JsonResponse
from django.template.loader import render_to_string
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from users.decorators import auth_required
from users.models import User
from users.serializers import UserSerializer
from users.tasks import send_verification_email

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
def test_user_following_extracted(user_factory):
    user1 = user_factory()
    user2 = user_factory()

    user_main = user_factory(following=[user2])

    assert user2 in user_main.following.all()
    assert user_main.following.count() == 1


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
    me.following.add(santi, elena)

    pedro = User.objects.create_user(username='pedro', email='pedro@test.com')
    santi.following.add(pedro)
    elena.following.add(pedro)

    maria = User.objects.create_user(username='maria', email='maria@test.com')
    elena.following.add(maria)

    juan = User.objects.create_user(username='juan', email='juan@test.com')
    santi.following.add(juan)
    me.following.add(juan)

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
    assert not serialized['following']


@pytest.mark.django_db
def test_user_serializer_is_following(user_factory):
    user = user_factory()
    user_request = user_factory()
    user_request.following.add(user)
    user_request.save()
    request = SimpleNamespace(user=user_request)
    serialized = UserSerializer(user, request=request).serialize()

    assert serialized['id'] == user.pk
    assert serialized['username'] == user.username
    assert serialized['bio'] == user.bio
    assert serialized['following']


# ===========================================================================
# DECORATORS
# ===========================================================================
@pytest.fixture
def mock_view_auth_required():

    @auth_required
    def view(request):
        return JsonResponse(
            {'username': request.user.username, 'user_id': request.user.id}, status=HTTPStatus.OK
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
    assert json.loads(response.content)['error'] == 'Token is invalid or have an incorrect padding'


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

    assert sent_email.subject == f'Verificación de MoviesXMovies de {user.username}'
    assert sent_email.to == [user.email]
    assert sent_email.content_subtype == 'html'

    expected_html = render_to_string('users/email/verification-email.html', {'user': user})
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

    auth_client.user.following.add(user1, user2)
    user1.following.add(user3)
    user2.following.add(user3)

    url = SUGGESTED_USERS_URL
    response = auth_client.get(url)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['count'] == 1
    assert len(response.json()['results']) == 1
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
        auth_client.user.following.add(bridge_user)

        bridge_user.following.add(*targets)

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
    response = auth_client.get(SELF_USER_DETAIL_URL)
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
    }

    response = auth_client.post(SIGNUP_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == 2
    assert response.json()['username'] == 'test'


@pytest.mark.django_db
def test_user_signup_exception(auth_client):
    payload = {
        'email': 'testexample.com',
        'username': 'test',
        'first_name': 'test',
        'last_name': 'test',
    }

    response = auth_client.post(SIGNUP_URL, data=payload, content_type='application/json')
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['email'] == ['Enter a valid email address.']


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
