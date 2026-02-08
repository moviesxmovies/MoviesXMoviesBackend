import pytest

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
