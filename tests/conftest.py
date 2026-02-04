import pytest

from users.models import User

# ===========================================
# URLS
# ===========================================

LOGIN_URL = '/api/auth/login/'
REFRESH_URL = '/api/auth/refresh/'


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
