from http import HTTPStatus

from django.core.cache import cache
from django.db.models import Case, IntegerField, Q, When
from django.forms import ValidationError
from django.http import JsonResponse
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiParameter, extend_schema, OpenApiTypes
from rest_framework import serializers
from rest_framework.decorators import api_view

from movielists.models import MovieList
from movies.models import Movie
from movies.serializers import MovieSerializer
from ratings.models import Rating
from ratings.serializers import RatingSerializer
from reviews.models import Review
from reviews.serializers import ReviewSerializer
from shared.decorators import cached_view, get_body, get_query_params, require_http_methods
from shared.utils import get_paginated_response, get_progressive_response
from users.decorators import auth_required

LIMIT_RECOMMENDATIONS = 20


class ReviewSaveSerializer(serializers.Serializer):
    """Serializer for validating review creation payloads.

    Attributes:
        is_positive (serializers.BooleanField): Whether the review is positive.
        title (serializers.CharField): Title of the review.
        content (serializers.CharField): Body content of the review.
    """

    is_positive = serializers.BooleanField(
        required=True, help_text='If the serializer is positive or not'
    )
    title = serializers.CharField(required=True, help_text='Title of review')
    content = serializers.CharField(required=True, help_text='Content of review')


class RatingSaveSerializer(serializers.Serializer):
    """Serializer for validating rating creation and update payloads.

    Attributes:
        rating (serializers.IntegerField): Numeric rating value between 1 and 5.
    """

    rating = serializers.IntegerField(
        required=True, help_text='Rating value between 1 and 5', min_value=1, max_value=5
    )


class MoviesInListSerializer(serializers.ModelSerializer):
    """Serializer for representing a Movie inside a movie list.

    Exposes a subset of movie fields suitable for list and recommendation
    display contexts.
    """

    class Meta:
        model = Movie
        fields = [
            'id',
            'title',
            'slug',
            'release_date',
            'synopsis',
            'cover',
            'genres',
            'awards',
            'platforms',
            'actors',
            'directors',
        ]


@extend_schema(
    responses={200: MovieSerializer.get_schema(), 404: None},
    description='Get details of a specific movie',
    operation_id='get_movie_detail',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@cached_view(
    lambda req, movie: f'movie_detail_{movie.pk}:{req.user.preferred_language}', timeout=60 * 60 * 6
)
def movie_detail(request, movie: Movie) -> JsonResponse:
    """Return the full detail representation of a single movie.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: Serialized movie data with HTTP 200.
    """
    return MovieSerializer(movie, request=request).json_response()


@extend_schema(
    responses={200: RatingSerializer.get_paginated_schema(), 400: None, 404: None},
    description='Get ratings of friends for a specific movie',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit')
@cached_view(
    make_key=lambda req, movie, page=1, limit=10: (
        f'friends_ratings:{req.user.pk}:{movie.pk}:{page}:{limit}'
    ),
    timeout=60 * 5,
)
def movie_friends_ratings(request, movie: Movie, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of friend ratings for a specific movie.

    Only ratings from users in request.user.friends are included,
    ordered by most recently created first.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized ratings with HTTP 200.
    """
    ratings_query = movie.ratings.filter(user__in=request.user.friends.all()).order_by(
        '-created_at'
    )
    return get_paginated_response(ratings_query, RatingSerializer, request, page, limit)


@extend_schema(
    methods=['GET'],
    description='Get reviews specific movie paginated',
    parameters=[
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
        OpenApiParameter(
            name='last_id',
            description='ID of the last item from the previous page',
            required=False,
            type=int,
        ),
    ],
    responses={200: ReviewSerializer.get_progressive_pagination_schema(), 404: None},
    operation_id='get_movie_reviews',
)
@extend_schema(
    methods=['POST'],
    description='Create Review of a movie',
    responses={201: ReviewSerializer.get_schema(), 400: None},
    request=ReviewSaveSerializer,
    operation_id='create_movie_review',
)
@api_view(['GET', 'POST'])
@auth_required
def movie_review_wrapper(request, movie: Movie) -> JsonResponse:
    """Route GET and POST review requests to their respective handlers.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: The response from movie_reviews on GET,
        or from save_movie_review on POST.
    """
    match request.method:
        case 'POST':
            return save_movie_review(request, movie)
        case 'GET':
            return movie_reviews(request, movie)


@require_http_methods(['GET'])
@get_query_params('limit', 'last_id')
@cached_view(
    make_key=lambda req, movie, limit=10, last_id=None: (
        f'movie_reviews:{movie.pk}:{limit}:{last_id}'
    ),
    timeout=60 * 5,
)
def movie_reviews(request, movie: Movie, limit=10, last_id=None):
    return get_progressive_response(
        Review.objects.filter(movie=movie), ReviewSerializer, request, last_id, limit
    )


@require_http_methods(['POST'])
@get_body(Review, ['is_positive', 'title', 'content'])
def save_movie_review(request, movie: Movie, review: Review) -> JsonResponse:
    """Persist a new review for a movie and return it serialized.

    The review instance is injected by the get_body decorator using
    the 'is_positive', 'title', and 'content' fields from the request body.
    user and movie are assigned before saving.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.
        review (Review): Unsaved Review instance constructed from the
            request body by get_body.

    Returns:
        JsonResponse: Serialized new review with HTTP 201.
    """
    review.user = request.user
    review.movie = movie
    try:
        review.full_clean()
    except ValidationError as e:
        return JsonResponse(e.message_dict, status=HTTPStatus.BAD_REQUEST)
    review.save()
    response = ReviewSerializer(review, request=request).json_response()
    response.status_code = 201
    return response


@extend_schema(
    methods=['GET'],
    description='Get self rating for a specific movie',
    responses={200: RatingSerializer.get_schema(), 404: None},
    operation_id='get_movie_rating',
)
@extend_schema(
    methods=['POST'],
    description='Create self rating for a specific movie',
    request=RatingSaveSerializer,
    responses={201: RatingSerializer.get_schema(), 400: None, 404: None},
    operation_id='create_movie_rating',
)
@extend_schema(
    methods=['PUT'],
    description='Update self rating for a specific movie',
    request=RatingSaveSerializer,
    responses={200: RatingSerializer.get_schema(), 400: None, 404: None},
    operation_id='update_movie_rating',
)
@api_view(['GET', 'POST', 'PUT'])
@auth_required
def movie_rating_wrapper(request, movie: Movie) -> JsonResponse:
    """Route GET, POST, and PUT rating requests to their respective handlers.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: The response from the matched rating handler.
    """
    match request.method:
        case 'GET':
            return get_self_movie_rating(request, movie)
        case 'POST':
            return create_movie_rating(request, movie)
        case 'PUT':
            return update_movie_rating(request, movie)


@require_http_methods(['GET'])
@cached_view(lambda req, movie: f'movie_rating:{req.user.pk}:{movie.pk}', timeout=60 * 5)
def get_self_movie_rating(request, movie: Movie) -> JsonResponse:
    """Return the authenticated user's own rating for a specific movie.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: Serialized rating with HTTP 200, or a JSON error
        body with HTTP 404 if no rating exists.
    """
    try:
        rating = movie.ratings.get(user=request.user)
        return RatingSerializer(rating, request=request).json_response()
    except Rating.DoesNotExist:
        return JsonResponse({'error': _('Rating not found')}, status=HTTPStatus.NOT_FOUND)


@require_http_methods(['POST'])
@get_body(Rating, ['rating'])
def create_movie_rating(request, movie: Movie, rating: Rating) -> JsonResponse:
    """Create and persist the authenticated user's rating for a movie.

    Rejects the request if the user has already rated the movie.
    Runs full_clean() before saving to enforce model-level validation.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.
        rating (Rating): Unsaved Rating instance constructed from the
            request body by get_body.

    Returns:
        JsonResponse: Serialized new rating with HTTP 201, or a JSON error
        body with HTTP 400 on duplicate or validation failure.
    """
    if movie.ratings.filter(user=request.user).exists():
        return JsonResponse(
            {'error': _('You have already rated this movie')}, status=HTTPStatus.BAD_REQUEST
        )
    rating.user = request.user
    rating.movie = movie
    try:
        rating.full_clean()
    except ValidationError as e:
        return JsonResponse(e.message_dict, status=HTTPStatus.BAD_REQUEST)
    rating.save()
    response = RatingSerializer(rating, request=request).json_response()
    response.status_code = 201
    return response


@require_http_methods(['PUT'])
@get_body(Rating, ['rating'])
def update_movie_rating(request, movie: Movie, rating: Rating) -> JsonResponse:
    """Update the authenticated user's existing rating for a movie.

    Fetches the persisted rating, applies the new value from the injected
    rating instance, runs full_clean(), and saves.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.
        rating (Rating): Unsaved Rating instance carrying the new value,
            constructed by get_body.

    Returns:
        JsonResponse: Serialized updated rating with HTTP 200, a JSON error
        body with HTTP 404 if no prior rating exists, or HTTP 400 on
        validation failure.
    """
    try:
        existing_rating = movie.ratings.get(user=request.user)
        existing_rating.rating = rating.rating
        existing_rating.full_clean()
        existing_rating.save()
        return RatingSerializer(existing_rating, request=request).json_response()
    except Rating.DoesNotExist:
        return JsonResponse({'error': _('Rating not found')}, status=HTTPStatus.NOT_FOUND)
    except ValidationError as e:
        return JsonResponse(e.message_dict, status=HTTPStatus.BAD_REQUEST)


@extend_schema(
    description='Get movie recommendations for the authenticated user',
    responses={200: MoviesInListSerializer(many=True), 400: None},
    operation_id='get_movie_recommendations',
)
@api_view(['GET'])
@auth_required
@require_http_methods(['GET'])
@cached_view(
    make_key=lambda req: f'recommendations:{req.user.pk}:{req.user.preferred_language}',
    timeout=60 * 30,
)
def get_movie_recommendations(request) -> JsonResponse:
    """Return a ranked list of movie recommendations for the authenticated user.

    Pipeline:
        1. Build exclusion set (already watched / marked unseen).
        2. Fetch ML candidates from cache, fall back to recency ordering.
        3. Score and sort candidates.
        4. Pad with algorithmic results if the model returns fewer than
           LIMIT_RECOMMENDATIONS.
        5. Re-query Movie preserving the scored order.
        6. Return serialized response.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: Serialized list of up to LIMIT_RECOMMENDATIONS
        recommended movies with HTTP 200.
    """
    user = request.user

    proxy = MovieList(user=user)

    exclude_ids = proxy._get_exclude_ids()
    candidates_qs = proxy._get_base_candidates(exclude_ids)
    candidates_qs = proxy._apply_hard_filters(candidates_qs, genres=None)
    scored_movies = proxy._score_candidates(
        candidates_qs,
        celebrities=None,
        friends=list(request.user.friends.values_list('username', flat=True)),
    )

    recommended = [movie for movie, _score in scored_movies]
    if len(recommended) < LIMIT_RECOMMENDATIONS:
        recommended = _pad_with_algorithmic(recommended, exclude_ids, user, LIMIT_RECOMMENDATIONS)

    ordered_ids = [m.id for m in recommended]
    preserved_order = Case(
        *[When(id=pk, then=pos) for pos, pk in enumerate(ordered_ids)],
        output_field=IntegerField(),
    )
    queryset = (
        Movie.objects.filter(id__in=ordered_ids)
        .annotate(recommendation_rank=preserved_order)
        .order_by('recommendation_rank')[:LIMIT_RECOMMENDATIONS]
    )

    return MovieSerializer(queryset, request=request).json_response()


def _pad_with_algorithmic(
    existing: list[Movie],
    exclude_ids: set[int],
    user,
    needed: int,
) -> list[Movie]:
    """Pad a recommendations list with algorithmically selected fallback movies.

    Fills the gap between len(existing) and needed by querying recent movies
    available on the user's platforms, excluding already seen or existing
    candidates.

    Args:
        existing (list[Movie]): Movies already selected by the scoring pipeline.
        exclude_ids (set[int]): Primary-key set of movies to exclude.
        user: The authenticated user whose platforms relation is used to
            filter results.
        needed (int): Total number of recommendations required.

    Returns:
        list[Movie]: The existing list extended with up to
        needed - len(existing) additional Movie instances,
        ordered by -release_date.
    """
    existing_ids = {m.id for m in existing}

    user_platforms = user.platforms.values_list('slug', flat=True)

    fallback_qs = (
        Movie.objects.exclude(id__in=exclude_ids | existing_ids)
        .prefetch_related('actors', 'directors', 'awards', 'genres', 'platforms')
        .order_by('-release_date')
    )

    if user_platforms:
        fallback_qs = fallback_qs.filter(
            Q(platforms__slug__in=user_platforms) | Q(platforms__isnull=True)
        ).distinct()

    return existing + list(fallback_qs[: needed - len(existing)])


@extend_schema(
    description='Mark a movie as unseen',
    methods=['POST'],
    responses={200: bool, 400: None, 404: None},
    operation_id='mark_movie_unseen',
)
@extend_schema(
    description='Remove a movie from the unseen list',
    methods=['DELETE'],
    responses={200: bool, 400: None, 404: None},
    operation_id='unmark_movie_unseen',
)
@api_view(['POST', 'DELETE'])
@auth_required
@require_http_methods(['POST', 'DELETE'])
def movie_unseen_wrapper(request, movie: Movie) -> JsonResponse:
    """Handle marking a movie as unseen or removing it from the unseen list.

    If request method is POST, the movie is added to the user's unseen list.
    If request method is DELETE, the movie is removed from the unseen list.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    match request.method:
        case 'POST':
            response = mark_movie_unseen(request, movie)
        case 'DELETE':
            response = unmark_movie_unseen(request, movie)

    if isinstance(response, JsonResponse):
        return response

    cache.delete(f'recommendations:{request.user.pk}')
    return JsonResponse({'success': True}, status=HTTPStatus.OK)


@require_http_methods(['POST'])
def mark_movie_unseen(request, movie: Movie) -> JsonResponse:
    """Add a movie to the authenticated user's unseen list.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    user = request.user
    if user.unseen_movies.filter(pk=movie.pk).exists():
        return JsonResponse(
            {'error': _('Movie already marked as unseen')}, status=HTTPStatus.BAD_REQUEST
        )

    user.unseen_movies.add(movie)
    return True


@require_http_methods(['DELETE'])
def unmark_movie_unseen(request, movie: Movie) -> JsonResponse:
    """Remove a movie from the authenticated user's unseen list.

    Args:
        request: The authenticated incoming HTTP request.
        movie (Movie): The movie instance resolved from the URL.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    user = request.user
    if not user.unseen_movies.filter(pk=movie.pk).exists():
        return JsonResponse(
            {'error': _('Movie not marked as unseen')}, status=HTTPStatus.BAD_REQUEST
        )

    user.unseen_movies.remove(movie)
    return True


@extend_schema(
    description='Search for movies by params',
    parameters=[
        OpenApiParameter(
            name='genres',
            description='List of genre slugs to filter by',
            required=False,
            type=OpenApiTypes.STR,
            many=True,
            location=OpenApiParameter.QUERY,
            style='form',
            explode=True,
        ),
        OpenApiParameter(
            name='platforms',
            description='List of platform slugs to filter by',
            required=False,
            type=OpenApiTypes.STR,
            many=True,
            location=OpenApiParameter.QUERY,
            style='form',
            explode=True,
        ),
        OpenApiParameter(
            name='directors',
            description='List of director slugs to filter by',
            required=False,
            type=OpenApiTypes.STR,
            many=True,
            location=OpenApiParameter.QUERY,
            style='form',
            explode=True,
        ),
        OpenApiParameter(
            name='actors',
            description='List of actor slugs to filter by',
            required=False,
            type=OpenApiTypes.STR,
            many=True,
            location=OpenApiParameter.QUERY,
            style='form',
            explode=True,
        ),
        OpenApiParameter(
            name='marked_unseen',
            description='Whether to include only movies marked as unseen',
            required=False,
            type=bool,
        ),
        OpenApiParameter(
            name='stars',
            description='List of star ratings (1-5) to filter by',
            required=False,
            type=OpenApiTypes.INT,
            many=True,
            location=OpenApiParameter.QUERY,
            style='form',
            explode=True,
        ),
        OpenApiParameter(
            name='reviewed',
            description='Whether to include only movies the user has reviewed',
            required=False,
            type=bool,
        ),
        OpenApiParameter(
            name='name',
            description='The name of the movie to search for',
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name='page',
            description='The page number to retrieve (for pagination)',
            required=False,
            type=int,
        ),
        OpenApiParameter(
            name='limit',
            description='The number of items per page (for pagination)',
            required=False,
            type=int,
        ),
    ],
    responses={200: MovieSerializer.get_schema(), 400: None},
    operation_id='search_movies',
)
@api_view(['GET'])
@auth_required
@require_http_methods(['GET'])
@get_query_params(
    'marked_unseen',
    'reviewed',
    'name',
    'page',
    'limit',
)
def movie_search(
    request,
    marked_unseen: bool | None = None,
    reviewed: bool | None = None,
    name: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> JsonResponse:
    """Search for movies matching the specified query parameters.

    Supports filtering by genres, platforms, directors, actors, unseen status,
    user ratings, reviews, and name.

    Args:
        request: The authenticated incoming HTTP request.
        genres: Optional list of genre slugs to filter by.
        platforms: Optional list of platform slugs to filter by.
        directors: Optional list of director names to filter by.
        actors: Optional list of actor names to filter by.
        marked_unseen: If true, include only movies marked as unseen by the user.
        stars: Optional dict mapping star ratings (1-5) to booleans indicating
            whether to include movies with that rating from the user.
        reviewed: If true, include only movies reviewed by the user.
        name: Optional substring to search for in movie titles.
    Returns:
        JsonResponse: Paginated serialized list of movies matching the search criteria with HTTP 200,
        or a JSON error body with HTTP 400 on invalid parameters.
    """
    user = request.user
    movies_qs = Movie.objects.all()
    genres = request.GET.getlist('genres')
    platforms = request.GET.getlist('platforms')
    directors = request.GET.getlist('directors')
    actors = request.GET.getlist('actors')
    stars = request.GET.getlist('stars')

    if genres:
        movies_qs = movies_qs.filter(genres__slug__in=genres)
    if platforms:
        movies_qs = movies_qs.filter(platforms__slug__in=platforms)
    if directors:
        movies_qs = movies_qs.filter(directors__slug__in=directors)
    if actors:
        movies_qs = movies_qs.filter(actors__slug__in=actors)

    if marked_unseen == 'true':
        movies_qs = movies_qs.filter(users_unseen=user)
    if stars:
        rating_filters = Q()
        for star in stars:
            rating_filters |= Q(ratings__user=user, ratings__rating=star)
        movies_qs = movies_qs.filter(rating_filters)
    if reviewed == 'true':
        movies_qs = movies_qs.filter(reviews__user=user)
    if name:
        movies_qs = movies_qs.filter(
            Q(title__icontains=name)
            | Q(translations__title__icontains=name, translations__language=user.preferred_language)
        )

    movies_qs = movies_qs.distinct().order_by('-release_date')

    return get_paginated_response(movies_qs, MovieSerializer, request, page, limit)
