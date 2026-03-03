from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from genres.models import Genre
from persons.models import Person
from shared.decorators import get_body, get_query_params, require_http_methods
from shared.utils import get_paginated_response
from users.decorators import auth_required
from drf_spectacular.utils import OpenApiParameter
from .models import MovieList
from .serializers import MovieListSerializer


class SaveMovieListSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=1024)
    privacity = serializers.ChoiceField(choices=MovieList.Privacity.choices)


@extend_schema(
    responses={200: MovieListSerializer.get_paginated_schema(), 404: None},
    description='Get a all movie list of the authenticated user',
    operation_id='get_self_movie_list_detail',
    methods=['GET'],
)
@extend_schema(
    request=SaveMovieListSerializer,
    responses={200: MovieListSerializer.get_schema(), 400: None},
    description='Create a movie list for the authenticated user',
    operation_id='create_self_movie_list',
    methods=['POST'],
    parameters=[
        OpenApiParameter(
            name='intelligent',
            type=bool,
            description='Whether to use intelligent movie list creation',
            required=False,
        ),
        OpenApiParameter(
            name='genres',
            type={'type': 'array', 'items': {'type': 'string'}},
            location=OpenApiParameter.QUERY,
            description='List of genres',
            required=False,
            explode=True,
        ),
        OpenApiParameter(
            name='celebrities',
            type={'type': 'array', 'items': {'type': 'string'}},
            location=OpenApiParameter.QUERY,
            description='List of celebrities',
            required=False,
            explode=True,
        ),
        OpenApiParameter(
            name='friends',
            type={'type': 'array', 'items': {'type': 'string'}},
            location=OpenApiParameter.QUERY,
            description='List of friends usernames',
            required=False,
            explode=True,
        ),
    ],
)
@api_view(['GET', 'POST'])
@require_http_methods(['GET', 'POST'])
@auth_required
def movies_list_self_wrapper(request):
    match request.method:
        case 'GET':
            return movies_list_self(request)
        case 'POST':
            return save_movie_list_self(request)


@get_query_params('page', 'limit')
def movies_list_self(request, page: int = 1, limit: int = 10):
    """Users movies Lists

    Args:
        request (django.request)): All about the request

    Returns:
        [movielists.models.MovieList]: A list of movies
    """
    return get_paginated_response(
        request.user.movies_lists.all(),
        MovieListSerializer,
        request=request,
        page=page,
        limit=limit,
    )


@get_body(MovieList, ['name', 'description', 'privacity'])
@get_query_params('intelligent')
def save_movie_list_self(request, movielist: MovieList, intelligent: bool = False):
    genres = request.GET.getlist('genres')
    celebrities = request.GET.getlist('celebrities')
    friends = request.GET.getlist('friends')

    movielist.user = request.user
    movielist.slug = slugify(movielist.name)

    try:
        movielist.full_clean()

        if intelligent:
            error_response = _validate_intelligent_params(
                request.user, genres, celebrities, friends
            )
            if error_response:
                return error_response

        movielist.save()

        if intelligent:
            movielist.intelligent_fill(genres=genres, celebrities=celebrities, friends=friends)
        response = MovieListSerializer(movielist, request=request).json_response()
        response.status_code = HTTPStatus.CREATED
        return response

    except ValidationError as e:
        return JsonResponse(e.message_dict, status=HTTPStatus.BAD_REQUEST)


def _validate_intelligent_params(user, genres, celebrities, friends):
    if genres:
        existing_genres = set(Genre.objects.filter(slug__in=genres).values_list('slug', flat=True))
        for g in genres:
            if g not in existing_genres:
                return JsonResponse(
                    {'error': f'Genre `{g}` does not exist'}, status=HTTPStatus.BAD_REQUEST
                )

    if celebrities:
        existing_celebs = set(
            Person.objects.filter(slug__in=celebrities).values_list('slug', flat=True)
        )
        for c in celebrities:
            if c not in existing_celebs:
                return JsonResponse(
                    {'error': f'Celebrity `{c}` does not exist'}, status=HTTPStatus.BAD_REQUEST
                )

    if friends:
        existing_friends = set(
            user.friends.filter(username__in=friends).values_list('username', flat=True)
        )
        for f in friends:
            if f not in existing_friends:
                return JsonResponse(
                    {'error': f'Friend `{f}` is not in your list'}, status=HTTPStatus.BAD_REQUEST
                )

    return None


@extend_schema(
    responses={200: MovieListSerializer.get_paginated_schema(), 404: None},
    description='Get a specific movie list of a user',
    operation_id='get_self_movie_list_detail',
)
@api_view()
@require_http_methods(['GET'])
@get_query_params('page', 'limit')
@auth_required
def movies_list_list(request, user, page: int = 1, limit: int = 10):
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

    return get_paginated_response(
        movies_lists,
        MovieListSerializer,
        request=request,
        page=page,
        limit=limit,
    )


@extend_schema(
    responses={200: MovieListSerializer.get_schema(), 404: None},
    description='Get a specific movie list of a user',
    operation_id='get_movie_list_detail',
)
@api_view()
@require_http_methods(['GET'])
@auth_required
def movies_list_detail(request, user, movies_list):
    """A detail of a movie list

    Args:
        request (): User request
        user (_type_): The user which owns the list
        movies_list (_type_): The movie list to retrieve

    Returns:
        django.http.JsonResponse: The serialized movie list
    """
    if request.user == user:
        return MovieListSerializer(movies_list, request=request).json_response()
    match movies_list.privacity:
        case MovieList.Privacity.PUBLIC:
            return MovieListSerializer(movies_list, request=request).json_response()
        case MovieList.Privacity.FOLLOWERS:
            if user.is_friend(request.user):
                return MovieListSerializer(movies_list, request=request).json_response()

    return JsonResponse(
        {'error': "This movies list doesn't exist or you're not allowed to see it"},
        status=HTTPStatus.NOT_FOUND,
    )


@extend_schema(
    responses={200: MovieListSerializer.get_schema(), 400: None, 404: None},
    description='Add a movie from a movie list',
    operation_id='add_movie_to_list',
    methods=['POST'],
)
@extend_schema(
    responses={200: bool, 400: None, 404: None},
    description='Remove a movie from a movie list',
    operation_id='remove_movie_from_list',
    methods=['DELETE'],
)
@api_view(['POST', 'DELETE'])
@require_http_methods(['POST', 'DELETE'])
@auth_required
def movies_list_movie_wrapper(request, user, movies_list, movie):
    if request.user != user:
        return JsonResponse(
            {'error': "This movies list doesn't exist or you're not allowed to see it"},
            status=HTTPStatus.NOT_FOUND,
        )
    match request.method:
        case 'POST':
            return add_movie_to_list(request, movies_list, movie)
        case 'DELETE':
            return remove_movie_from_list(request, movies_list, movie)


@require_http_methods(['POST'])
def add_movie_to_list(request, movies_list, movie):
    movies_list.movies.add(movie)
    movies_list.save()
    return MovieListSerializer(movies_list, request=request).json_response()


@require_http_methods(['DELETE'])
def remove_movie_from_list(request, movies_list, movie):
    movies_list.movies.remove(movie)
    movies_list.save()
    return JsonResponse({'success': True})
