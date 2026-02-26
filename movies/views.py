from django.core.paginator import Paginator
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view


from movies.models import Movie
from movies.serializers import MovieSerializer
from reviews.serializers import ReviewSerializer
from shared.decorators import get_query_params, require_http_methods
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
    reviews_query = movie.reviews.all().order_by('-created_at')
    if not page or not str(page).isdigit():
        page = 1
    else:
        page = int(page)
    if not limit or not str(limit).isdigit():
        limit = 10
    else:
        limit = int(limit)

    paginator = Paginator(reviews_query, limit)
    page_result = paginator.get_page(page)
    serialized_reviews = [
        ReviewSerializer(review, request=request).serialize() for review in page_result.object_list
    ]
    return JsonResponse(
        {
            'results': serialized_reviews,
            'total_pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': page_result.has_next(),
            'has_previous': page_result.has_previous(),
            'current_page': page_result.number,
        }
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
    friends = request.user.friends.all()
    reviews_query = movie.reviews.filter(user__in=friends).order_by('-created_at')
    if not page or not str(page).isdigit():
        page = 1
    else:
        page = int(page)
    if not limit or not str(limit).isdigit():
        limit = 10
    else:
        limit = int(limit)

    paginator = Paginator(reviews_query, limit)
    page_result = paginator.get_page(page)
    serialized_reviews = [
        ReviewSerializer(review, request=request).serialize() for review in page_result.object_list
    ]
    return JsonResponse(
        {
            'results': serialized_reviews,
            'total_pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': page_result.has_next(),
            'has_previous': page_result.has_previous(),
            'current_page': page_result.number,
        }
    )
