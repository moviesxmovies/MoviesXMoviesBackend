from http import HTTPStatus

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view

from movies.models import Movie
from movies.serializers import MovieSerializer
from ratings.models import Rating
from ratings.serializers import RatingSerializer
from reviews.models import Review
from reviews.serializers import ReviewSerializer
from shared.decorators import get_body, get_query_params, require_http_methods
from shared.utils import get_paginated_response
from users.decorators import auth_required
from rest_framework import serializers


class ReviewSaveSerializer(serializers.Serializer):
    is_positive = serializers.BooleanField(
        required=True, help_text='If the serializer is positive or not'
    )
    title = serializers.CharField(required=True, help_text='Title of review')
    content = serializers.CharField(required=True, help_text='Content of review')


class RatingSaveSerializer(serializers.Serializer):
    rating = serializers.IntegerField(
        required=True, help_text='Rating value between 1 and 5', min_value=1, max_value=5
    )


@extend_schema(
    responses={200: MovieSerializer.get_schema(), 404: None},
    description='Get details of a specific movie',
    operation_id='get_movie_detail',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
def movie_detail(request, movie: Movie):
    return MovieSerializer(movie, request=request).json_response()


# RATINGS
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
def movie_friends_ratings(request, movie: Movie, page: int = 1, limit: int = 10):
    ratings_query = movie.ratings.filter(user__in=request.user.friends.all()).order_by(
        '-created_at'
    )
    return get_paginated_response(ratings_query, RatingSerializer, request, page, limit)


# REVIEWS
@extend_schema(
    methods=['GET'],
    description='Get reviews specific movie paginated',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
    responses={200: ReviewSerializer.get_paginated_schema(), 404: None},
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
def movie_review_wrapper(request, movie: Movie):
    match request.method:
        case 'POST':
            return save_movie_review(request, movie)
        case 'GET':
            return movie_reviews(request, movie)


@require_http_methods(['GET'])
@get_query_params('page', 'limit')
def movie_reviews(request, movie: Movie, page: int = 1, limit: int = 10):
    return get_paginated_response(
        movie.reviews.all().order_by('-created_at'), ReviewSerializer, request, page, limit
    )


@require_http_methods(['POST'])
@get_body(Review, ['is_positive', 'title', 'content'])
def save_movie_review(request, movie: Movie, review: Review):
    review.user = request.user
    review.movie = movie
    review.save()
    response = ReviewSerializer(review, request=request).json_response()
    response.status_code = 201
    return response


# RATINGS
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
def movie_rating_wrapper(request, movie: Movie):
    match request.method:
        case 'GET':
            return get_self_movie_rating(request, movie)
        case 'POST':
            return create_movie_rating(request, movie)
        case 'PUT':
            return update_movie_rating(request, movie)


@require_http_methods(['GET'])
def get_self_movie_rating(request, movie: Movie):
    try:
        rating = movie.ratings.get(user=request.user)
        return RatingSerializer(rating, request=request).json_response()
    except Rating.DoesNotExist:
        return JsonResponse({'error': 'Rating not found'}, status=HTTPStatus.NOT_FOUND)


@require_http_methods(['POST'])
@get_body(Rating, ['rating'])
def create_movie_rating(request, movie: Movie, rating: Rating):
    if movie.ratings.filter(user=request.user).exists():
        return JsonResponse({'error': 'Rating already exists'}, status=HTTPStatus.BAD_REQUEST)
    rating.user = request.user
    rating.movie = movie
    rating.save()
    response = RatingSerializer(rating, request=request).json_response()
    response.status_code = 201
    return response


@require_http_methods(['PUT'])
@get_body(Rating, ['rating'])
def update_movie_rating(request, movie: Movie, rating: Rating):
    try:
        existing_rating = movie.ratings.get(user=request.user)
        existing_rating.rating = rating.rating
        existing_rating.save()
        return RatingSerializer(existing_rating, request=request).json_response()
    except Rating.DoesNotExist:
        return JsonResponse({'error': 'Rating not found'}, status=HTTPStatus.NOT_FOUND)
