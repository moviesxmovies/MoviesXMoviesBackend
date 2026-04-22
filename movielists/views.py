from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from genres.models import Genre
from persons.models import Person
from shared.decorators import cached_view, get_body, get_query_params, require_http_methods
from shared.utils import get_paginated_response
from users.decorators import auth_required

from .models import MovieList
from .serializers import MovieListSerializer


class SaveMovieListSerializer(serializers.Serializer):
    """Serializer for validating movie list creation and update payloads.

    Attributes:
        name (serializers.CharField): Name of the movie list.
        description (serializers.CharField): Description of the movie list.
        privacity (serializers.ChoiceField): Visibility setting from
            ``MovieList.Privacity.choices``.
    """

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
            name='genres[]',
            type={'type': 'array', 'items': {'type': 'string'}},
            location=OpenApiParameter.QUERY,
            description='List of genres',
            required=False,
            explode=True,
        ),
        OpenApiParameter(
            name='celebrities[]',
            type={'type': 'array', 'items': {'type': 'string'}},
            location=OpenApiParameter.QUERY,
            description='List of celebrities',
            required=False,
            explode=True,
        ),
        OpenApiParameter(
            name='friends[]',
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
@auth_required()
def movies_list_self_wrapper(request) -> JsonResponse:
    """Route GET and POST movie list requests to their respective handlers.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: The response from ``movies_list_self`` on GET,
        or from ``save_movie_list_self`` on POST.
    """
    match request.method:
        case 'GET':
            return movies_list_self(request)
        case 'POST':
            return save_movie_list_self(request)


@get_query_params('page', 'limit')
@cached_view(
    lambda req, page, limit: f'movies_lists_self:{req.user.pk}:{page}:{limit}', timeout=60 * 60
)
def movies_list_self(request, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of all movie lists owned by the authenticated user.

    Args:
        request: The authenticated incoming HTTP request.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized movie lists with HTTP 200.
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
def save_movie_list_self(request, movielist: MovieList, intelligent: str) -> JsonResponse:
    """Create and persist a new movie list for the authenticated user.

    Optionally fills the list intelligently using genres, celebrities, and
    friends query parameters when ``intelligent`` is truthy. Validates all
    parameters before saving.

    Args:
        request: The authenticated incoming HTTP request. May include
            ``genres``, ``celebrities``, and ``friends`` as multi-value
            query parameters when ``intelligent`` is set.
        movielist (MovieList): Unsaved ``MovieList`` instance constructed
            from the request body by ``get_body``.
        intelligent (str): Query parameter controlling intelligent fill.
            Treated as ``False`` when absent or equal to ``'false'``.

    Returns:
        JsonResponse: Serialized new movie list with HTTP 201, or a JSON
        error body with HTTP 400 on validation failure or invalid parameters.
    """
    genres = request.GET.getlist('genres[]')
    celebrities = request.GET.getlist('celebrities[]')
    friends = request.GET.getlist('friends[]')

    movielist.user = request.user
    movielist.slug = slugify(movielist.name)

    is_intelligent = bool(intelligent) and intelligent.lower() != 'false'

    try:
        movielist.full_clean()

        if is_intelligent:
            error_response = _validate_intelligent_params(
                request.user, genres, celebrities, friends
            )
            if error_response:
                return error_response

        movielist.save()

        if is_intelligent:
            movielist.intelligent_fill(genres=genres, celebrities=celebrities, friends=friends)
        response = MovieListSerializer(movielist, request=request).json_response()
        response.status_code = HTTPStatus.CREATED
        return response

    except ValidationError as e:
        return JsonResponse(e.message_dict, status=HTTPStatus.BAD_REQUEST)


def _validate_intelligent_params(
    user, genres: list[str], celebrities: list[str], friends: list[str]
) -> JsonResponse | None:
    """Validate that all provided slugs and usernames exist in the database.

    Checks each genre slug against ``Genre``, each celebrity slug against
    ``Person``, and each friend username against the user's friend list.
    Returns the first error response encountered, or ``None`` if all are valid.

    Args:
        user: The authenticated user whose friends relation is used to
            validate friend usernames.
        genres (list[str]): List of genre slugs to validate.
        celebrities (list[str]): List of celebrity slugs to validate.
        friends (list[str]): List of friend usernames to validate.

    Returns:
        JsonResponse: A JSON error body with HTTP 400 for the first invalid
        value found, or ``None`` if all values are valid.
    """
    if genres:
        existing_genres = set(Genre.objects.filter(slug__in=genres).values_list('slug', flat=True))
        for g in genres:
            if g not in existing_genres:
                return JsonResponse(
                    {'error': _('Genre `{g}` does not exist').format(g=g)},
                    status=HTTPStatus.BAD_REQUEST,
                )

    if celebrities:
        existing_celebs = set(
            Person.objects.filter(slug__in=celebrities).values_list('slug', flat=True)
        )
        for c in celebrities:
            if c not in existing_celebs:
                return JsonResponse(
                    {'error': _('Celebrity `{c}` does not exist').format(c=c)},
                    status=HTTPStatus.BAD_REQUEST,
                )

    if friends:
        existing_friends = set(
            user.friends.filter(username__in=friends).values_list('username', flat=True)
        )
        for f in friends:
            if f not in existing_friends:
                return JsonResponse(
                    {'error': _('Friend `{f}` is not in your list').format(f=f)},
                    status=HTTPStatus.BAD_REQUEST,
                )

    return None


@extend_schema(
    responses={200: MovieListSerializer.get_paginated_schema(), 404: None},
    description='Get a specific movie list of a user',
    operation_id='get_self_movie_list_list',
)
@api_view()
@require_http_methods(['GET'])
@get_query_params('page', 'limit')
@auth_required()
@cached_view(
    lambda req, user, page, limit: f'movies_lists_user:{user.pk}:{page}:{limit}:{req.user.pk}',
    timeout=60 * 60,
)
def movies_list_list(request, user, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of movie lists belonging to a specific user.

    Filters lists by privacity based on the relationship between the
    authenticated user and the target user. Owners see all lists; friends
    see public and followers-only lists; others see only public lists.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user whose movie lists are being retrieved,
            resolved from the URL.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized movie lists with HTTP 200.
    """
    if request.user == user:
        return MovieListSerializer(user.movies_lists.all(), request=request).json_response()
    movies_lists = user.movies_lists.exclude(privacity=MovieList.Privacity.PRIVATE).all()
    if not user.is_friend(request.user):
        movies_lists = movies_lists.exclude(privacity=MovieList.Privacity.FRIENDS)

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
@auth_required()
@cached_view(
    lambda req, user, movies_list: f'movies_lists_detail:{user.pk}:{movies_list.pk}:{req.user.pk}',
    timeout=60 * 60,
)
def movies_list_detail(request, user, movies_list: MovieList) -> JsonResponse:
    """Return the detail of a specific movie list, enforcing privacity rules.

    Owners always have access. Public lists are visible to everyone.
    Followers-only lists are visible only to friends of the owner.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user who owns the movie list, resolved from the URL.
        movies_list (MovieList): The movie list instance resolved from the URL.

    Returns:
        JsonResponse: Serialized movie list with HTTP 200, or a JSON error
        body with HTTP 404 if the list is private or the requester is not
        allowed to view it.
    """
    if request.user == user:
        return MovieListSerializer(movies_list, request=request).json_response()
    match movies_list.privacity:
        case MovieList.Privacity.PUBLIC:
            return MovieListSerializer(movies_list, request=request).json_response()
        case MovieList.Privacity.FRIENDS:
            if user.is_friend(request.user):
                return MovieListSerializer(movies_list, request=request).json_response()

    return JsonResponse(
        {'error': _("This movies list doesn't exist or you're not allowed to see it")},
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
@auth_required()
def movies_list_movie_wrapper(request, user, movies_list: MovieList, movie) -> JsonResponse:
    """Route POST and DELETE movie-in-list requests to their respective handlers.

    Rejects the request if the authenticated user is not the owner of both
    the list and the user record.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user who owns the movie list, resolved from the URL.
        movies_list (MovieList): The movie list instance resolved from the URL.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: The response from ``add_movie_to_list`` on POST, or
        from ``remove_movie_from_list`` on DELETE, or a JSON error body
        with HTTP 403 if the requester is not the list owner.
    """
    if request.user != user or movies_list.user != user:
        return JsonResponse(
            {'error': _("This movies list doesn't exist or you're not allowed to see it")},
            status=HTTPStatus.FORBIDDEN,
        )
    match request.method:
        case 'POST':
            return add_movie_to_list(request, movies_list, movie)
        case 'DELETE':
            return remove_movie_from_list(request, movies_list, movie)


@require_http_methods(['POST'])
def add_movie_to_list(request, movies_list: MovieList, movie) -> JsonResponse:
    """Add a movie to a movie list and return the updated list.

    Args:
        request: The authenticated incoming HTTP request.
        movies_list (MovieList): The movie list to add the movie to.
        movie (Movie): The movie instance to add.

    Returns:
        JsonResponse: Serialized updated movie list with HTTP 200.
    """
    movies_list.movies.add(movie)
    movies_list.save()
    return MovieListSerializer(movies_list, request=request).json_response()


@require_http_methods(['DELETE'])
def remove_movie_from_list(request, movies_list: MovieList, movie) -> JsonResponse:
    """Remove a movie from a movie list and confirm success.

    Args:
        request: The authenticated incoming HTTP request.
        movies_list (MovieList): The movie list to remove the movie from.
        movie (Movie): The movie instance to remove.

    Returns:
        JsonResponse: ``{'success': True}`` with HTTP 200.
    """
    movies_list.movies.remove(movie)
    movies_list.save()
    return JsonResponse({'success': True})
