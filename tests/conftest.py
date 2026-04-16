import re
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.cache.backends.locmem import LocMemCache
from pytest_factoryboy import register

from factories import (
    AwardFactory,
    CommentFactory,
    GenreFactory,
    GenreTranslationFactory,
    MovieFactory,
    MovieListFactory,
    MovieTranslationFactory,
    PersonFactory,
    PlatformFactory,
    RatingFactory,
    ReactionFactory,
    ReviewFactory,
    UserFactory,
    FriendRequestFactory,
)
from factories.persons import PersonTranslationFactory
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
register(MovieTranslationFactory)
register(GenreTranslationFactory)
register(CommentFactory)
register(ReactionFactory)
register(FriendRequestFactory)
register(PersonTranslationFactory)

# ===========================================
# URLS
# ===========================================

# SWAGGET/ADMIN
SWAGGER_URL = '/api/docs/'
ADMIN_URL = '/admin/'
SCHEMA_URL = '/api/schema/'

# AUTH
LOGIN_URL = '/api/auth/login/'
SIGNUP_URL = '/api/auth/signup/'
REFRESH_URL = '/api/auth/refresh/'
VERIFY_USER_URL = '/api/auth/verify/'
RESEND_VERIFICATION_EMAIL_URL = '/api/auth/resend-verification-email/'
FORGOT_PASSWORD_URL = '/api/auth/forgot-password/'


# MOVIE LISTS
MOVIE_LIST_SELF_URL = '/api/movies-lists/'
MOVIE_LIST_USER_URL = '/api/movies-lists/{username}/'
MOVIE_LIST_DETAIL_URL = '/api/movies-lists/{username}/{movies_list_slug}/'
MOVIE_LIST_MOVIE_WRAPPER_URL = '/api/movies-lists/{username}/{movies_list_slug}/{movie_slug}/'

# MOVIES
MOVIE_RECOMMENDATIONS_URL = '/api/movies/'
MOVIE_SEARCHING_URL = '/api/movies/searching/'
MOVIE_DETAIL_URL = '/api/movies/{movie_slug}/'
MOVIE_REVIEWS_URL = '/api/movies/{movie_slug}/reviews/'
MOVIE_FRIENDS_RATINGS_URL = '/api/movies/{movie_slug}/friends-ratings/'
MOVIE_SELF_RATING_URL = '/api/movies/{movie_slug}/ratings/'
MOVIE_UNSEEN_URL = '/api/movies/{movie_slug}/unseen/'
MOVIE_MOVIE_LISTS_URL = '/api/movies/{movie_slug}/movie-lists/'

# USERS
SUGGESTED_USERS_URL = '/api/users/suggested-users/'
SELF_USER_WRAPPER_URL = '/api/users/'
USER_DETAIL_URL = '/api/users/{username}/'
USER_REVIEWS_URL = '/api/users/{username}/reviews/'
USER_PREFERRED_LANGUAGE_URL = '/api/users/preferred-language/'
USER_ONBOARDING_URL = '/api/users/onboarding/'
USER_SEARCH_URL = '/api/users/searching/'
USER_FRIENDS_URL = '/api/users/{username}/friends/'
USER_FRIEND_REQUESTS_URL = '/api/users/{username}/friend-requests/'


# REVIEWS - COMMENTS - REACTIONS
EDIT_DELETE_REVIEW_URL = '/api/reviews/{review_id}/'
REVIEW_COMMENTS_URL = '/api/reviews/{review_id}/comments/'
REVIEW_COMMENT_DETAIL_URL = '/api/reviews/{review_id}/comments/{comment_id}/'
REVIEW_COMMENT_REPLIES_URL = '/api/reviews/{review_id}/comments/{comment_id}/replies/'
REVIEW_REACTIONS_URL = '/api/reviews/{review_id}/reactions/'
REVIEW_REACTION_DETAIL_URL = '/api/reviews/{review_id}/reactions/{reaction_id}/'
COMMENT_REACTIONS_URL = '/api/reviews/{review_id}/comments/{comment_id}/reactions/'
COMMENT_REACTION_DETAIL_URL = (
    '/api/reviews/{review_id}/comments/{comment_id}/reactions/{reaction_id}/'
)

# GENRES
GENRES_LIST_URL = '/api/genres/'

# PLATFORMS
PLATFORMS_LIST_URL = '/api/platforms/'

# PERSONS
PERSON_DETAIL_URL = '/api/persons/{person_slug}/'
PERSON_ACTORS_SEARCH_URL = '/api/persons/actors/'
PERSON_DIRECTORS_SEARCH_URL = '/api/persons/directors/'
PERSON_ACTED_MOVIES_URL = '/api/persons/{person_slug}/acted-movies/'
PERSON_DIRECTED_MOVIES_URL = '/api/persons/{person_slug}/directed-movies/'

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

    user.verified = True
    user.save()

    token = generate_jwt(user)

    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    client.user = user

    return client


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def disable_social_jobs():
    signal_handler = 'users.signals.send_verification_email_on_created'
    delay = 'users.tasks.send_verification_email.delay'
    delay2 = 'users.tasks.send_password_reset_email.delay'
    with (
        mock.patch(signal_handler) as mock_handler,
        mock.patch(delay) as mock_delay,
        mock.patch(delay2) as mock_delay2,
    ):
        yield {'handler': mock_handler, 'delay': mock_delay, 'delay2': mock_delay2}


class ExtendedLocMemCache(LocMemCache):
    def keys(self, pattern):
        with self._lock:
            all_keys = list(self._cache.keys())

        regex = re.escape(pattern).replace(r'\*', '.*')
        return [k for k in all_keys if re.fullmatch(regex, k)]
