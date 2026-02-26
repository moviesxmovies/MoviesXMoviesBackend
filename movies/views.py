from django.core.paginator import Paginator
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view

from movies.models import Movie
from movies.serializers import MovieSerializer
from ratings.serializers import RatingSerializer
from reviews.serializers import ReviewSerializer
from shared.decorators import get_query_params, require_http_methods
from shared.utils import get_paginated_response
from users.decorators import auth_required


@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
def movie_detail(request, movie: Movie):
    return MovieSerializer(movie, request=request).json_response()


@extend_schema(
    responses={200: None, 400: None},
    description='Get paginated reviews for a specific movie',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit')
def movie_reviews(request, movie: Movie, page: int = 1, limit: int = 10):
    return get_paginated_response(
        movie.reviews.all().order_by('-created_at'), ReviewSerializer, request, page, limit
    )


@extend_schema(
    responses={200: None, 400: None, 404: None},
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
    ratings_query = movie.ratings.filter(user__in=request.user.friends.all()).order_by('-created_at')
    return get_paginated_response(ratings_query, RatingSerializer, request, page, limit)
