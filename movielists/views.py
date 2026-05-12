from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from genres.models import Genre
from movies.serializers import MovieSerializer
from persons.models import Person
from shared.decorators import cached_view, get_body, get_query_params, require_http_methods
from shared.utils import get_object_or_json_404, get_paginated_response, get_progressive_response
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


NOT_ALLOWED_TO_SEEE = "This movies list doesn't exist or you're not allowed to see it"


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
            user.get_friends().filter(username__in=friends).values_list('username', flat=True)
        )
        for f in friends:
            if f not in existing_friends:
                return JsonResponse(
                    {'error': _('Friend `{f}` is not in your list').format(f=f)},
                    status=HTTPStatus.BAD_REQUEST,
                )

    return None


@extend_schema(
    responses={200: MovieListSerializer.get_progressive_pagination_schema(), 404: None},
    description='Get a specific movie list of a user',
    operation_id='get_self_movie_list_list',
)
@api_view()
@require_http_methods(['GET'])
@get_query_params('last_id', 'limit')
@auth_required()
@cached_view(
    lambda req, user, last_id, limit: (
        f'movies_lists_user:{user.pk}:{last_id}:{limit}:{req.user.pk}'
    ),
    timeout=60 * 60,
)
def movies_list_list(request, user, last_id: int = None, limit: int = 10) -> JsonResponse:
    """Return a paginated list of movie lists belonging to a specific user.

    Filters lists by privacity based on the relationship between the
    authenticated user and the target user. Owners see all lists; friends
    see public and followers-only lists; others see only public lists.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user whose movie lists are being retrieved,
            resolved from the URL.
        last_id (int): The last ID for progressive pagination. Defaults to None.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized movie lists with HTTP 200.
    """
    if request.user == user:
        return get_progressive_response(
            user.movies_lists.all(),
            MovieListSerializer,
            request=request,
            last_id=last_id,
            limit=limit,
        )
    movies_lists = user.movies_lists.exclude(privacity=MovieList.Privacity.PRIVATE).all()
    if not user.is_friend(request.user):
        movies_lists = movies_lists.exclude(privacity=MovieList.Privacity.FRIENDS)

    return get_progressive_response(
        movies_lists,
        MovieListSerializer,
        request=request,
        last_id=last_id,
        limit=limit,
    )


@extend_schema(
    responses={200: MovieListSerializer.get_schema(), 404: None},
    description='Get a specific movie list of a user',
    operation_id='get_movie_list_detail',
    methods=['GET'],
)
@extend_schema(
    responses={200: None, 403: None, 404: None},
    description='Delete a specific movie list of a user',
    operation_id='delete_movie_list',
    methods=['DELETE'],
)
@api_view(['GET', 'DELETE'])
@require_http_methods(['GET', 'DELETE'])
@auth_required()
def movies_list_wrapper(request, user, movies_list_slug: str) -> JsonResponse:
    """Wrapper for handling movie list requests.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user who owns the movie list, resolved from the URL.
        movies_list_slug (str): The slug of the movie list, resolved from the URL.

    Returns:
        JsonResponse: The response from the appropriate handler.
    """
    movies_list = get_object_or_json_404(MovieList, user=user, slug=movies_list_slug)
    match request.method:
        case 'GET':
            return movies_list_detail(request, user, movies_list)
        case 'DELETE':
            return delete_movie_list_self(request, user, movies_list)


@require_http_methods(['GET'])
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
        {'error': _(NOT_ALLOWED_TO_SEEE)},
        status=HTTPStatus.NOT_FOUND,
    )


@require_http_methods(['DELETE'])
def delete_movie_list_self(request, user, movies_list: MovieList) -> JsonResponse:
    """Delete a movie list if the requester is the owner.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user who owns the movie list, resolved from the URL.
        movies_list (MovieList): The movie list instance resolved from the URL.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    if request.user != user:
        return JsonResponse(
            {'error': _(NOT_ALLOWED_TO_SEEE)},
            status=HTTPStatus.NOT_FOUND,
        )
    movies_list.hard_delete()
    return JsonResponse({'success': True}, status=HTTPStatus.OK)


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
def movies_list_movie_wrapper(request, user, movies_list_slug: str, movie) -> JsonResponse:
    """Route POST and DELETE movie-in-list requests to their respective handlers.

    Rejects the request if the authenticated user is not the owner of both
    the list and the user record.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user who owns the movie list, resolved from the URL.
        movies_list_slug (str): The slug of the movie list, resolved from the URL.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: The response from ``add_movie_to_list`` on POST, or
        from ``remove_movie_from_list`` on DELETE, or a JSON error body
        with HTTP 403 if the requester is not the list owner.
    """
    movies_list = get_object_or_json_404(MovieList, user=user, slug=movies_list_slug)
    if request.user != user or movies_list.user != user:
        return JsonResponse(
            {'error': _(NOT_ALLOWED_TO_SEEE)},
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


@extend_schema(
    responses={200: MovieListSerializer.get_paginated_schema(), 404: None},
    description='Search movie lists of the authenticated user by name',
    operation_id='search_self_movie_lists',
    methods=['GET'],
    parameters=[
        OpenApiParameter(
            name='query',
            type=str,
            description='Search query to match against movie list names',
            required=True,
        ),
        OpenApiParameter(
            name='page',
            type=int,
            description='Page number for pagination. Defaults to 1.',
            required=False,
        ),
        OpenApiParameter(
            name='limit',
            type=int,
            description='Number of items per page. Defaults to 10.',
            required=False,
        ),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@get_query_params('query', 'page', 'limit')
@auth_required()
@cached_view(
    lambda req, query, page, limit: f'movies_lists_search:{req.user.pk}:{query}:{page}:{limit}',
    timeout=60 * 60,
)
def movies_list_search(request, query: str, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of the authenticated user's movie lists matching a query.

    Args:
        request: The authenticated incoming HTTP request.
        query (str): The search query to match against movie list names.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized movie lists with HTTP 200.
    """
    if not query:
        query = ''
    movies_lists = MovieList.objects.filter(name__icontains=query)
    return get_paginated_response(
        movies_lists,
        MovieListSerializer,
        request=request,
        page=page,
        limit=limit,
    )


@extend_schema(
    responses={200: MovieListSerializer.get_paginated_schema(), 404: None},
    description='Search movies in a movie list by title',
    operation_id='search_movies_in_list',
    methods=['GET'],
    parameters=[
        OpenApiParameter(
            name='query',
            type=str,
            description='Search query to match against movie titles in the list',
            required=True,
        ),
        OpenApiParameter(
            name='page',
            type=int,
            description='Page number for pagination. Defaults to 1.',
            required=False,
        ),
        OpenApiParameter(
            name='limit',
            type=int,
            description='Number of items per page. Defaults to 10.',
            required=False,
        ),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@get_query_params('query', 'page', 'limit')
@auth_required()
@cached_view(
    lambda req, user, movies_list_slug, query, page, limit: (
        f'movies_lists_movies_search:{user.pk}:{movies_list_slug}:{query}:{page}:{limit}:{req.user.pk}:{req.user.preferred_language}'
    ),
    timeout=60 * 60,
)
def movies_list_movie_search(
    request, user, movies_list_slug: str, query: str, page: int = 1, limit: int = 10
) -> JsonResponse:
    """Return a paginated list of movies in a movie list matching a search query.

    Enforces the same privacity rules as ``movies_list_detail`` to determine
    if the requester can view the list. If allowed, filters the movies in the
    list by title matching the query.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user who owns the movie list, resolved from the URL.
        movies_list_slug (str): The slug of the movie list, resolved from the URL.
        query (str): The search query to match against movie titles in the list.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized movies with HTTP 200, or a JSON
        error body with HTTP 404 if the list is private or the requester is
        not allowed to view it.
    """
    movies_list = get_object_or_json_404(MovieList, user=user, slug=movies_list_slug)
    if not query:
        query = ''
    if request.user == user:
        movies_qs = movies_list.movies.filter(
            Q(title__icontains=query)
            | Q(
                translations__title__icontains=query,
                translations__language=request.user.preferred_language,
            )
        )
    else:
        match movies_list.privacity:
            case MovieList.Privacity.PUBLIC:
                movies_qs = movies_list.movies.filter(
                    Q(title__icontains=query)
                    | Q(
                        translations__title__icontains=query,
                        translations__language=request.user.preferred_language,
                    )
                )
            case MovieList.Privacity.FRIENDS:
                if user.is_friend(request.user):
                    movies_qs = movies_list.movies.filter(
                        Q(title__icontains=query)
                        | Q(
                            translations__title__icontains=query,
                            translations__language=request.user.preferred_language,
                        )
                    )
                else:
                    return JsonResponse(
                        {'error': _(NOT_ALLOWED_TO_SEEE)},
                        status=HTTPStatus.NOT_FOUND,
                    )
            case MovieList.Privacity.PRIVATE:
                return JsonResponse(
                    {'error': _(NOT_ALLOWED_TO_SEEE)},
                    status=HTTPStatus.NOT_FOUND,
                )

    return get_paginated_response(
        movies_qs.distinct(),
        MovieSerializer,
        request=request,
        page=page,
        limit=limit,
    )
