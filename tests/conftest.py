from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
import pytest
from django.conf import settings
from pytest_factoryboy import register

from factories import (
    AwardFactory,
    GenreFactory,
    MovieFactory,
    MovieListFactory,
    PersonFactory,
    PlatformFactory,
    RatingFactory,
    ReviewFactory,
    UserFactory,
)
from users.models import User

register(UserFactory)
register(MovieFactory)
register(PersonFactory)
register(GenreFactory)
register(RatingFactory)
register(ReviewFactory)
register(AwardFactory)
register(PlatformFactory)
register(MovieListFactory)

# ===========================================
# URLS
# ===========================================

LOGIN_URL = '/api/auth/login/'
REFRESH_URL = '/api/auth/refresh/'
MOVIE_LIST_SELF_URL = '/api/movies-lists/'
MOVIE_LIST_USER_URL = '/api/movies-lists/{username}/'
MOVIE_LIST_DETAIL_URL = '/api/movies-lists/{username}/{movies_list_slug}/'

VERIFY_USER_URL = '/api/auth/verify/'


# ===========================================
# TEST USERS
# ===========================================

TEST_USER_USERNAME = 'testuser'
TEST_USER_PASSWORD = 'testpassword123'
TEST_USER_EMAIL = 'test@mail.es'


# ===========================================
# FIXTURES
# ===========================================


@pytest.fixture(autouse=True)
def disable_drf_throttling(settings):
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'anon': None,
        'user': None,
    }


@pytest.fixture
def create_test_user(db):
    user = User.objects.create_user(
        username=TEST_USER_USERNAME, password=TEST_USER_PASSWORD, email=TEST_USER_EMAIL
    )
    return user


@pytest.fixture
def generate_jwt():
    def _generate_jwt(user):
        payload = {
            'user_id': user.id,
            'token_type': 'access',
            'exp': datetime.now(timezone.utc) + timedelta(days=1),
            'iat': datetime.now(timezone.utc),
            'jti': str(user.id) + '-' + str(datetime.now(timezone.utc).timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return _generate_jwt


@pytest.fixture
def auth_client(client, user_factory, generate_jwt):
    """
    Creates a test user, generates a JWT for that user, and configures the test client to use that JWT for authentication in subsequent requests.
    """
    user = user_factory()

    token = generate_jwt(user)

    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    client.user = user

    return client


@pytest.fixture(autouse=True)
def disable_redis_jobs():
    target = 'users.tasks.send_verification_email.delay'

    with mock.patch(target, return_value=None) as mocked_job:
        yield mocked_job
