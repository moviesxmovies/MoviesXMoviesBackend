from http import HTTPStatus

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from reviews.models import Review
from reviews.serializers import ReviewSerializer
from shared.decorators import get_body, require_http_methods
from users.decorators import auth_required


class ReviewUpdateSerializer(serializers.Serializer):
    is_positive = serializers.BooleanField(
        required=True, help_text='If the review is positive or not'
    )
    title = serializers.CharField(required=True, help_text='Title of review')
    content = serializers.CharField(required=True, help_text='Content of review')


class ReviewDeleteSerializer(serializers.Serializer):
    status = serializers.BooleanField(required=True, help_text='Status of the review deletion')


# REVIEWS WITH ID
@extend_schema(
    methods=['PUT'],
    request=ReviewUpdateSerializer,
    responses={200: ReviewSerializer.get_schema(), 400: None},
    description='Update a review for a specific movie',
    operation_id='update_movie_review',
)
@extend_schema(
    methods=['DELETE'],
    responses={204: ReviewDeleteSerializer, 404: None},
    description='Delete a review for a specific movie',
    operation_id='delete_movie_review',
)
@api_view(['PUT', 'DELETE'])
@auth_required
def review_wrapper(request, review: Review):
    match request.method:
        case 'PUT':
            return edit_review(request, review)
        case 'DELETE':
            return delete_review(request, review)


@require_http_methods(['PUT'])
@get_body(None, ['is_positive', 'title', 'content'])
def edit_review(request, review: Review, body):
    if review.user != request.user:
        return JsonResponse(
            {'error': 'You can only edit your own reviews'}, status=HTTPStatus.FORBIDDEN
        )
    review.is_positive = body['is_positive']
    review.title = body['title']
    review.content = body['content']
    review.save()
    return ReviewSerializer(review, request=request).json_response()


@require_http_methods(['DELETE'])
def delete_review(request, review: Review):
    if review.user != request.user:
        return JsonResponse(
            {'error': 'You can only delete your own reviews'}, status=HTTPStatus.FORBIDDEN
        )
    review.delete()
    return JsonResponse({'status': True}, status=HTTPStatus.NO_CONTENT)
