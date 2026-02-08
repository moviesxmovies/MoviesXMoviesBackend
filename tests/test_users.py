import pytest
from conftest import LOGIN_URL, REFRESH_URL, TEST_USER_PASSWORD, TEST_USER_USERNAME
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

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
