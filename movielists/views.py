from http import HTTPStatus

from django.http import JsonResponse
from rest_framework.decorators import api_view

from shared.decorators import require_http_methods
from users.decorators import auth_required

from .models import MovieList
from .serializers import MovieListSerializer


@api_view()
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


@api_view()
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
    movies_lists = user.movies_lists.exclude(privacity=MovieList.Privacity.PRIVATE).all()
    if not user.is_friend(request.user):
        movies_lists = movies_lists.exclude(privacity=MovieList.Privacity.FOLLOWERS)

    return MovieListSerializer(movies_lists, request=request).json_response()


@api_view()
@require_http_methods('GET')
@auth_required
def movies_list_detail(request, user, movies_list):
    if request.user == user:
        return MovieListSerializer(movies_list, request=request).json_response()
    match movies_list.privacity:
        case MovieList.Privacity.PUBLIC:
            return MovieListSerializer(movies_list, request=request).json_response()
        case MovieList.Privacity.FOLLOWERS:
            if not user.is_friend(request.user):
                return MovieListSerializer(movies_list, request=request).json_response()

    return JsonResponse(
        {'error': "This movies list doesn't exist or you're not allowed to see it"},
        status=HTTPStatus.NOT_FOUND,
    )
