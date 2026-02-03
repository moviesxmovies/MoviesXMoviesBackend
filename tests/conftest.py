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

ADMIN_USER_USERNAME = 'adminuser'
ADMIN_USER_PASSWORD = 'adminpassword123'


# ===========================================
# FIXTURES
# ===========================================


@pytest.fixture
def create_test_user(db):
    user = User.objects.create_user(username=TEST_USER_USERNAME, password=TEST_USER_PASSWORD)
    return user


@pytest.fixture
def create_admin_user(db):
    admin_user = User.objects.create_superuser(
        username=ADMIN_USER_USERNAME, password=ADMIN_USER_PASSWORD
    )
    return admin_user
