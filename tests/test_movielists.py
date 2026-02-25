import pytest
from conftest import MOVIE_LIST_DETAIL_URL, MOVIE_LIST_SELF_URL, MOVIE_LIST_USER_URL

from movielists.models import MovieList
from movielists.serializers import MovieListSerializer

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  MOVIELIST
# ===========================================================================


@pytest.mark.django_db
def test_movielist_creation(movie_list_factory):
    movielist = movie_list_factory()
    assert movielist.name is not None
    assert movielist.slug is not None
    assert movielist.description is not None
    assert movielist.privacity is not None
    assert movielist.user is not None
    assert movielist.movies.count() >= 0
    assert movielist.deleted_at is None
    assert movielist.created_at is not None
    assert movielist.updated_at is not None


@pytest.mark.django_db
def test_movie_list_build_skips_relations(movie_list_factory):
    movie_list = movie_list_factory.build()

    assert movie_list.pk is None


@pytest.mark.django_db
def test_movie_list_with_extracted_movies(movie_list_factory, movie_factory):
    MOVIE_TITLE = 'Inception'
    specific_movie = movie_factory(title=MOVIE_TITLE)

    movie_list = movie_list_factory(movies=[specific_movie])
    assert movie_list.movies.count() == 1
    assert movie_list.movies.first().title == MOVIE_TITLE


@pytest.mark.django_db
def test_movie_list_str(movie_list_factory):
    movie_list = movie_list_factory(name='My Movie List')
    assert str(movie_list) == 'my-movie-list'


# ===========================================================================
#  SERIALIZERS
# ===========================================================================
@pytest.mark.django_db
def test_movielist_serializer(movie_list_factory):
    movie_list = movie_list_factory(name='My Movie List')
    serialized = MovieListSerializer(movie_list).serialize()

    assert serialized['id'] == movie_list.pk
    assert serialized['name'] == 'My Movie List'
    assert serialized['slug'] == 'my-movie-list'
    assert serialized['privacity'] == movie_list.privacity
    assert serialized['user']['username'] == movie_list.user.username
    assert isinstance(serialized['movies'], list)
    assert serialized['created_at'] == movie_list.created_at.isoformat()
    assert serialized['updated_at'] == movie_list.updated_at.isoformat()


# ===========================================================================
#  VIEWS
# ===========================================================================

# ===========================================================================
#  MOVIELISTS
# ===========================================================================

# ===========================================================================
#  MOVIELIST SELF
# ===========================================================================


@pytest.mark.django_db
def test_movies_list_self_view(auth_client, movie_list_factory):
    user = auth_client.user

    movie_list_factory(user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE)
    movie_list_factory(user=user, name='My Movie List2', privacity=MovieList.Privacity.PUBLIC)
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FOLLOWERS)

    response = auth_client.get(MOVIE_LIST_SELF_URL)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    names = [list_item['name'] for list_item in data]
    assert 'My Movie List' in names
    assert 'My Movie List2' in names
    assert 'My Movie List3' in names


@pytest.mark.django_db
def test_movies_list_self_view_no_auth(client):
    response = client.get(MOVIE_LIST_SELF_URL)

    assert response.status_code == 401
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'You need to be authenticated'


# ===========================================================================
#  MOVIELIST LIST
# ===========================================================================


@pytest.mark.django_db
def test_movies_list_user_public_view(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')

    movie_list_factory(user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE)
    movie_list_factory(user=user, name='My Movie List2', privacity=MovieList.Privacity.PUBLIC)
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FOLLOWERS)

    response = auth_client.get(MOVIE_LIST_USER_URL.format(username=user.username))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['name'] == 'My Movie List2'


@pytest.mark.django_db
def test_movies_list_user_followers_view(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')
    user_auth = auth_client.user
    user.following.add(user_auth)
    user.save()
    user_auth.following.add(user)
    user_auth.save()

    movie_list_factory(user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE)
    movie_list_factory(user=user, name='My Movie List2', privacity=MovieList.Privacity.PUBLIC)
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FOLLOWERS)

    response = auth_client.get(MOVIE_LIST_USER_URL.format(username=user.username))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [list_item['name'] for list_item in data]
    assert 'My Movie List2' in names
    assert 'My Movie List3' in names


@pytest.mark.django_db
def test_movies_list_user_self(auth_client, movie_list_factory):
    user = auth_client.user

    movie_list_factory(user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE)
    movie_list_factory(user=user, name='My Movie List2', privacity=MovieList.Privacity.PUBLIC)
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FOLLOWERS)

    response = auth_client.get(MOVIE_LIST_USER_URL.format(username=user.username))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [list_item['name'] for list_item in data]
    assert 'My Movie List' in names
    assert 'My Movie List2' in names
    assert 'My Movie List3' in names


# ===========================================================================
#  MOVIELIST DETAIL
# ===========================================================================


@pytest.mark.django_db
def test_movies_list_detail_view_public(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')

    movie_list = movie_list_factory(
        user=user, name='My Movie List', privacity=MovieList.Privacity.PUBLIC
    )

    response = auth_client.get(
        MOVIE_LIST_DETAIL_URL.format(username=user.username, movies_list_slug=movie_list.slug)
    )
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'My Movie List'


@pytest.mark.django_db
def test_movies_list_detail_view_followers(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')
    user_auth = auth_client.user
    user.following.add(user_auth)
    user.save()
    user_auth.following.add(user)
    user_auth.save()

    movie_list = movie_list_factory(
        user=user, name='My Movie List', privacity=MovieList.Privacity.FOLLOWERS
    )

    response = auth_client.get(
        MOVIE_LIST_DETAIL_URL.format(username=user.username, movies_list_slug=movie_list.slug)
    )
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'My Movie List'


@pytest.mark.django_db
def test_movies_list_detail_view_followers_forbidden(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')

    movie_list = movie_list_factory(
        user=user, name='My Movie List', privacity=MovieList.Privacity.FOLLOWERS
    )

    response = auth_client.get(
        MOVIE_LIST_DETAIL_URL.format(username=user.username, movies_list_slug=movie_list.slug)
    )
    assert response.status_code == 404
    data = response.json()
    assert data['error'] == "This movies list doesn't exist or you're not allowed to see it"


@pytest.mark.django_db
def test_movies_list_detail_view_private(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')

    movie_list = movie_list_factory(
        user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE
    )

    response = auth_client.get(
        MOVIE_LIST_DETAIL_URL.format(username=user.username, movies_list_slug=movie_list.slug)
    )
    assert response.status_code == 404
    data = response.json()
    assert data['error'] == "This movies list doesn't exist or you're not allowed to see it"


@pytest.mark.django_db
def test_movies_list_detail_view_self(auth_client, movie_list_factory):
    user = auth_client.user

    movie_list = movie_list_factory(
        user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE
    )

    response = auth_client.get(
        MOVIE_LIST_DETAIL_URL.format(username=user.username, movies_list_slug=movie_list.slug)
    )
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'My Movie List'
