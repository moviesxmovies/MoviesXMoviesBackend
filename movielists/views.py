from shared.decorators import require_http_methods
from users.decorators import auth_required
from .models import MovieList
from .serializers import MovieListSerializer

@require_http_methods('GET')
@auth_required
def movies_list_self(request):
    """Users movies Lists

    Args:
        request (django.request)): All about the request

    Returns:
        [movielists.models.MovieList]: A list of movies
    """
    return MovieListSerializer(request.user.movies_lists.all(), request=request).json_response()

@require_http_methods('GET')
@auth_required
def movies_list_list(request, user):
    """Get user movie lists

    Args:
        request (djago.request): All about the request
        user (users.models.User): The user which owns the lists

    Returns:
        [movielists.models.MovieList]: A list of movies
    """
    if request.user == user:
        return MovieListSerializer(user.movies_lists.all(), request=request).json_response()
    movies_lists = user.movies_lists.exclude(privacy=MovieList.Privacity.PRIVATE).all()
    if not user.is_followed_by(request.user):
        movies_lists.exclude(privacy=MovieList.Privacity.FOLLOWERS)

    return MovieListSerializer(movies_lists, request=request)


@require_http_methods('GET')
@auth_required
def movies_list_detail(request, user, movies_list):
    pass
