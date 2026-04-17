from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view

from movies.serializers import MovieSerializer
from persons.models import Person
from persons.serializers import PersonSerializer
from shared.decorators import cached_view, get_query_params, require_http_methods
from shared.utils import get_paginated_response, get_progressive_response
from users.decorators import auth_required


@extend_schema(
    responses={
        200: PersonSerializer.get_schema(),
        404: OpenApiResponse(description='Person not found.'),
    },
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@cached_view(
    lambda req, person: f'person_detail:{person.pk}:{req.user.preferred_language}',
    timeout=60 * 60 * 24,
)
def person_detail(request, person: Person):
    return PersonSerializer(person, request=request).json_response()


def _get_person_response(queryset, request, page: int, limit: int, name: str = None):
    if name:
        queryset = queryset.filter(name__icontains=name)
    queryset = queryset.order_by('name')
    return get_paginated_response(queryset, PersonSerializer, request, page=page, limit=limit)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name='page',
            description='Page number for pagination (default: 1).',
            required=False,
            type=int,
            default=1,
        ),
        OpenApiParameter(
            name='limit',
            description='Number of items per page (default: 10, max: 100).',
            required=False,
            type=int,
            default=10,
        ),
        OpenApiParameter(
            name='name',
            description='Filter actors by name substring (case-insensitive). Optional.',
            required=False,
            type=str,
        ),
    ],
    responses={
        200: PersonSerializer.get_paginated_schema(),
    },
    description='Returns a paginated list of actors. Optional query parameters: `page` (default: 1), `limit` (default: 10, max: 100), and `name` for filtering actors by name substring.',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit', 'name')
@cached_view(
    make_key=lambda req, page, limit, name: (
        f'actors_pagination:{page}:{limit}:{name}:{req.user.preferred_language}'
    ),
    timeout=60 * 60 * 24,
)
def actors_pagination(request, page: int = 1, limit: int = 10, name: str = None):
    queryset = Person.objects.filter(acted_movies__isnull=False).distinct()
    return _get_person_response(queryset, request, page, limit, name)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name='page',
            description='Page number for pagination (default: 1).',
            required=False,
            type=int,
            default=1,
        ),
        OpenApiParameter(
            name='limit',
            description='Number of items per page (default: 10, max: 100).',
            required=False,
            type=int,
            default=10,
        ),
        OpenApiParameter(
            name='name',
            description='Filter directors by name substring (case-insensitive). Optional.',
            required=False,
            type=str,
        ),
    ],
    responses={
        200: PersonSerializer.get_paginated_schema(),
    },
    description='Returns a paginated list of directors. Optional query parameters: `page` (default: 1), `limit` (default: 10, max: 100), and `name` for filtering directors by name substring.',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit', 'name')
@cached_view(
    make_key=lambda req, page, limit, name: (
        f'directors_pagination:{page}:{limit}:{name}:{req.user.preferred_language}'
    ),
    timeout=60 * 60 * 24,
)
def directors_pagination(request, page: int = 1, limit: int = 10, name: str = None):
    queryset = Person.objects.filter(directed_movies__isnull=False).distinct()
    return _get_person_response(queryset, request, page, limit, name)


# =============================================================================================================================================
# Progressive pagination for person's acted/directed movies
# =============================================================================================================================================


@extend_schema(
    responses={
        200: PersonSerializer.get_progressive_pagination_schema(),
        404: OpenApiResponse(description='Person not found.'),
    },
    description='Returns a paginated list of movies the person has acted in. Optional query parameters: `last_id` and `limit` (default: 10, max: 100).',
    parameters=[
        OpenApiParameter(
            name='last_id',
            description='Last ID for progressive pagination.',
            required=False,
            type=int,
        ),
        OpenApiParameter(
            name='limit',
            description='Number of items per page (default: 10, max: 100).',
            required=False,
            type=int,
            default=10,
        ),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('last_id', 'limit')
@cached_view(
    make_key=lambda req, person, last_id, limit: (
        f'person_acted_movies:{person.pk}:{last_id}:{limit}:{req.user.preferred_language}'
    ),
    timeout=60 * 60 * 24,
)
def person_acted_movies(request, person: Person, last_id: int = None, limit: int = 10):
    movies = person.acted_movies.all()
    return get_progressive_response(
        movies,
        MovieSerializer,
        request,
        last_id=last_id,
        limit=limit,
        ordering_field=['-release_date', '-title'],
    )


@extend_schema(
    responses={
        200: PersonSerializer.get_progressive_pagination_schema(),
        404: OpenApiResponse(description='Person not found.'),
    },
    description='Returns a paginated list of movies the person has directed. Optional query parameters: `last_id` and `limit` (default: 10, max: 100).',
    parameters=[
        OpenApiParameter(
            name='last_id',
            description='Last ID for progressive pagination.',
            required=False,
            type=int,
        ),
        OpenApiParameter(
            name='limit',
            description='Number of items per page (default: 10, max: 100).',
            required=False,
            type=int,
            default=10,
        ),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('last_id', 'limit')
@cached_view(
    make_key=lambda req, person, last_id, limit: (
        f'person_directed_movies:{person.pk}:{last_id}:{limit}:{req.user.preferred_language}'
    ),
    timeout=60 * 60 * 24,
)
def person_directed_movies(request, person: Person, last_id: int = None, limit: int = 10):
    movies = person.directed_movies.all()
    return get_progressive_response(
        movies,
        MovieSerializer,
        request,
        last_id=last_id,
        limit=limit,
        ordering_field=['-release_date', '-title'],
    )
