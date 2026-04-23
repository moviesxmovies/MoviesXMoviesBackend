import pytest
from conftest import (
    MOVIE_LIST_DETAIL_URL,
    MOVIE_LIST_MOVIE_WRAPPER_URL,
    MOVIE_LIST_SELF_URL,
    MOVIE_LIST_USER_URL,
)
from django.core.cache import cache
from django.urls import reverse

from movielists.models import MovieList
from movielists.serializers import MovieListSerializer
from movies.tasks import retrain_professional_model
from users.models import FriendShip

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


@pytest.mark.django_db
def test_movie_list_intelligent_fill_no_filters(
    movie_list_factory, user_factory, movie_factory, rating_factory, platform_factory, genre_factory
):
    netflix = platform_factory(slug='netflix')
    drama = genre_factory(name='Drama', slug='drama')
    user = user_factory()
    user.platforms.add(netflix)

    movie_watched = movie_factory(title='Watched Movie', genres=[drama])
    rating_factory(movie=movie_watched, user=user, rating=5)

    movie_unseen = movie_factory(title='Unseen Movie', genres=[drama])
    user.unseen_movies.add(movie_unseen)

    movie_recommendation = movie_factory(title='Recommended Movie', genres=[drama])
    movie_recommendation.platforms.add(netflix)

    movie_list = movie_list_factory(user=user, name='Intelligent List')

    movie_list.intelligent_fill()

    assert movie_list.movies.count() > 0
    assert movie_list.movies.filter(id=movie_recommendation.id).exists()


@pytest.mark.django_db
def test_movie_list_intelligent_fill_with_scoring_filters(
    movie_list_factory, user_factory, movie_factory, person_factory, rating_factory, award_factory
):
    user = user_factory()
    user.platforms.clear()

    friend = user_factory(username='best_friend')
    FriendShip.objects.create(user1=user, user2=friend)

    actor = person_factory(slug='leo-dicaprio')
    winner = movie_factory(title='The Perfect Movie')
    winner.actors.add(actor)

    award = award_factory(name='Best Picture')
    winner.awards.add(award)

    rating_factory(movie=winner, user=friend, rating=5)

    neutral_movie = movie_factory(title='Meh Movie')

    movie_list = movie_list_factory(user=user, name='Scored List')

    movie_list.intelligent_fill(celebrities=['leo-dicaprio'], friends=['best_friend'])

    movies = list(movie_list.movies.all())
    assert len(movies) >= 2
    assert movies[0] == winner


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
    assert serialized['user'].endswith(reverse('user-detail', args=[movie_list.user]))
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
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FRIENDS)

    response = auth_client.get(MOVIE_LIST_SELF_URL)

    assert response.status_code == 200
    data = response.json()

    assert data['count'] == 3
    names = [list_item['name'] for list_item in data['results']]
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
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FRIENDS)

    response = auth_client.get(MOVIE_LIST_USER_URL.format(username=user.username))
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 1
    assert data['results'][0]['name'] == 'My Movie List2'


@pytest.mark.django_db
def test_movies_list_user_followers_view(auth_client, movie_list_factory, user_factory):
    user = user_factory(username='otheruser')
    user_auth = auth_client.user
    FriendShip.objects.create(user1=user, user2=user_auth)

    movie_list_factory(user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE)
    movie_list_factory(user=user, name='My Movie List2', privacity=MovieList.Privacity.PUBLIC)
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FRIENDS)

    response = auth_client.get(MOVIE_LIST_USER_URL.format(username=user.username))
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 2
    names = [list_item['name'] for list_item in data['results']]
    assert 'My Movie List2' in names
    assert 'My Movie List3' in names


@pytest.mark.django_db
def test_movies_list_user_self(auth_client, movie_list_factory):
    user = auth_client.user

    movie_list_factory(user=user, name='My Movie List', privacity=MovieList.Privacity.PRIVATE)
    movie_list_factory(user=user, name='My Movie List2', privacity=MovieList.Privacity.PUBLIC)
    movie_list_factory(user=user, name='My Movie List3', privacity=MovieList.Privacity.FRIENDS)

    response = auth_client.get(MOVIE_LIST_USER_URL.format(username=user.username))
    assert response.status_code == 200
    data = response.json()
    results = data['results']
    assert len(results) == 3
    names = [list_item['name'] for list_item in results]
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
    FriendShip.objects.create(user1=user, user2=user_auth)

    movie_list = movie_list_factory(
        user=user, name='My Movie List', privacity=MovieList.Privacity.FRIENDS
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
        user=user, name='My Movie List', privacity=MovieList.Privacity.FRIENDS
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


@pytest.mark.django_db
def test_movies_list_save(auth_client):

    response = auth_client.post(
        MOVIE_LIST_SELF_URL,
        data={
            'name': 'My New Movie List',
            'description': 'A description for my new movie list',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'My New Movie List'
    assert data['description'] == 'A description for my new movie list'
    assert data['privacity'] == MovieList.Privacity.PUBLIC
    assert data['user'].endswith(reverse('user-detail', args=[auth_client.user]))
    assert data['movies'] == []


@pytest.mark.django_db
def test_movies_list_save_intelligent(auth_client, movie_factory, rating_factory, platform_factory, genre_factory):
    netflix = platform_factory(slug='netflix')
    drama = genre_factory(name='Drama', slug='drama')
    user = auth_client.user
    user.platforms.add(netflix)

    movie_watched = movie_factory(title='Watched Movie', genres=[drama])
    rating_factory(movie=movie_watched, user=user, rating=5)

    movie_unseen = movie_factory(title='Unseen Movie', genres=[drama])
    user.unseen_movies.add(movie_unseen)

    movie_recommendation = movie_factory(title='Recommended Movie', genres=[drama])
    movie_recommendation.platforms.add(netflix)

    response = auth_client.post(
        MOVIE_LIST_SELF_URL + '?intelligent=true',
        data={
            'name': 'My Intelligent Movie List',
            'description': 'A description for my intelligent movie list',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'My Intelligent Movie List'
    assert data['description'] == 'A description for my intelligent movie list'
    assert data['privacity'] == MovieList.Privacity.PUBLIC
    assert data['user'].endswith(reverse('user-detail', args=[auth_client.user]))
    assert len(data['movies']) > 0
    assert any(
        movie.endswith(reverse('movies:movie-detail', args=[movie_recommendation]))
        for movie in data['movies']
    )


@pytest.mark.django_db
def test_movie_list_save_using_cache(auth_client, user_factory, movie_factory, rating_factory):
    cache.clear()
    user = auth_client.user
    user.platforms.clear()

    watched_movies = [movie_factory(slug=f'already-watched-movie-{i}') for i in range(3)]
    unseen_movies = [movie_factory(slug=f'shiny-new-recommendation-{i}') for i in range(3)]

    comunidad = [user_factory() for _ in range(3)]

    for m in watched_movies:
        rating_factory(user=user, movie=m, rating=5)

    for u in comunidad:
        for m in watched_movies + unseen_movies:
            rating_factory(user=u, movie=m, rating=5)

    retrain_professional_model()

    response = auth_client.post(
        MOVIE_LIST_SELF_URL + '?intelligent=true',
        data={
            'name': 'AI Recommendation List',
            'description': 'Testing Implicit ALS',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 201
    data = response.json()

    recommended_urls = data['movies']
    assert len(recommended_urls) > 0, 'La IA no ha devuelto películas'

    watched_slugs = [m.slug for m in watched_movies]
    unseen_slugs = [m.slug for m in unseen_movies]

    for url in recommended_urls:
        for w_slug in watched_slugs:
            assert w_slug not in url, f'La película vista {w_slug} se coló en la recomendación'

    found_any_target = any(
        any(u_slug in url for u_slug in unseen_slugs) for url in recommended_urls
    )
    assert found_any_target, f'No se encontró ninguna recomendación esperada en: {recommended_urls}'

    cache.delete('movie_recommendation_model')


@pytest.mark.django_db
def test_movie_list_save_intelligent_fill_with_scoring_filters(
    movie_factory, person_factory, rating_factory, award_factory, auth_client, user_factory
):
    user = auth_client.user
    user.platforms.clear()

    friend = user_factory(username='best_friend')
    FriendShip.objects.create(user1=user, user2=friend)

    actor = person_factory(slug='leo-dicaprio')
    winner = movie_factory(title='The Perfect Movie')
    winner.actors.add(actor)
    award = award_factory(name='Best Picture')
    winner.awards.add(award)
    rating_factory(movie=winner, user=friend, rating=5)

    neutral_movie = movie_factory(title='Meh Movie')

    response = auth_client.post(
        MOVIE_LIST_SELF_URL + '?intelligent=true&celebrities=leo-dicaprio&friends[]=best_friend',
        data={
            'name': 'My Scored Intelligent Movie List',
            'description': 'A description for my scored intelligent movie list',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'My Scored Intelligent Movie List'
    assert data['description'] == 'A description for my scored intelligent movie list'
    assert data['privacity'] == MovieList.Privacity.PUBLIC
    assert data['user'].endswith(reverse('user-detail', args=[auth_client.user]))
    assert len(data['movies']) >= 2
    assert data['movies'][0].endswith(reverse('movies:movie-detail', args=[winner]))


@pytest.mark.django_db
def test_movie_list_save_intelligent_exception_genre(auth_client):
    response = auth_client.post(
        MOVIE_LIST_SELF_URL + '?intelligent=true&genres[]=nonexistentgenre',
        data={
            'name': 'My Intelligent Movie List',
            'description': 'A description for my intelligent movie list',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'Genre `nonexistentgenre` does not exist'


@pytest.mark.django_db
def test_movie_list_save_intelligent_exception_celebrities(auth_client):
    response = auth_client.post(
        MOVIE_LIST_SELF_URL + '?intelligent=true&celebrities[]=nonexistentcelebrity',
        data={
            'name': 'My Intelligent Movie List',
            'description': 'A description for my intelligent movie list',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'Celebrity `nonexistentcelebrity` does not exist'


@pytest.mark.django_db
def test_movie_list_save_intelligent_exception_friends(auth_client):
    response = auth_client.post(
        MOVIE_LIST_SELF_URL + '?intelligent=true&friends[]=nonexistentfriend',
        data={
            'name': 'My Intelligent Movie List',
            'description': 'A description for my intelligent movie list',
            'privacity': MovieList.Privacity.PUBLIC,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert data['error'] == 'Friend `nonexistentfriend` is not in your list'


@pytest.mark.django_db
def test_movie_list_add_movie(auth_client, movie_list_factory, movie_factory):
    user = auth_client.user
    movie_list = movie_list_factory(user=user)
    movie_list.movies.clear()

    movie = movie_factory()

    response = auth_client.post(
        MOVIE_LIST_MOVIE_WRAPPER_URL.format(
            username=user.username,
            movies_list_slug=movie_list.slug,
            movie_slug=movie.slug,
        ),
        content_type='application/json',
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data['movies']) == 1

    movie_url_part = reverse('movies:movie-detail', args=[movie])
    assert any(m.endswith(movie_url_part) for m in data['movies'])

    movie_list.refresh_from_db()
    assert movie_list.movies.count() == 1
    assert movie_list.movies.filter(id=movie.id).exists()


@pytest.mark.django_db
def test_movie_list_remove_movie(auth_client, movie_list_factory, movie_factory):
    user = auth_client.user
    movie_list = movie_list_factory(user=user)
    movie_list.movies.clear()

    movie = movie_factory()
    movie_list.movies.add(movie)

    response = auth_client.delete(
        MOVIE_LIST_MOVIE_WRAPPER_URL.format(
            username=user.username,
            movies_list_slug=movie_list.slug,
            movie_slug=movie.slug,
        ),
        content_type='application/json',
    )

    assert response.status_code == 200

    movie_list.refresh_from_db()
    assert movie_list.movies.count() == 0
    assert not movie_list.movies.filter(id=movie.id).exists()
