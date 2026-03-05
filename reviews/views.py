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
    """Serializer for validating review update payloads.

    Attributes:
        is_positive (serializers.BooleanField): Whether the review is positive.
        title (serializers.CharField): Updated title of the review.
        content (serializers.CharField): Updated body content of the review.
    """

    is_positive = serializers.BooleanField(
        required=True, help_text='If the review is positive or not'
    )
    title = serializers.CharField(required=True, help_text='Title of review')
    content = serializers.CharField(required=True, help_text='Content of review')


class ReviewDeleteSerializer(serializers.Serializer):
    """Serializer for the review deletion response payload.

    Attributes:
        status (serializers.BooleanField): Whether the deletion was successful.
    """

    status = serializers.BooleanField(required=True, help_text='Status of the review deletion')


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
def review_wrapper(request, review: Review) -> JsonResponse:
    """Route PUT and DELETE review requests to their respective handlers.

    Args:
        request: The authenticated incoming HTTP request.
        review (Review): The review instance resolved from the URL.

    Returns:
        JsonResponse: The response from ``edit_review`` on PUT,
        or from ``delete_review`` on DELETE.
    """
    match request.method:
        case 'PUT':
            return edit_review(request, review)
        case 'DELETE':
            return delete_review(request, review)


@require_http_methods(['PUT'])
@get_body(None, ['is_positive', 'title', 'content'])
def edit_review(request, review: Review, body: dict) -> JsonResponse:
    """Update the fields of an existing review.

    Only the owner of the review may edit it. Applies ``'is_positive'``,
    ``'title'``, and ``'content'`` from the request body and persists
    the changes.

    Args:
        request: The authenticated incoming HTTP request.
        review (Review): The review instance resolved from the URL.
        body (dict): Parsed request body containing ``'is_positive'``,
            ``'title'``, and ``'content'``, injected by ``get_body``.

    Returns:
        JsonResponse: Serialized updated review with HTTP 200, or a JSON
        error body with HTTP 403 if the requester is not the review owner.
    """
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
def delete_review(request, review: Review) -> JsonResponse:
    """Delete an existing review.

    Only the owner of the review may delete it.

    Args:
        request: The authenticated incoming HTTP request.
        review (Review): The review instance resolved from the URL.

    Returns:
        JsonResponse: ``{'status': True}`` with HTTP 204 on success, or a
        JSON error body with HTTP 403 if the requester is not the review owner.
    """
    if review.user != request.user:
        return JsonResponse(
            {'error': 'You can only delete your own reviews'}, status=HTTPStatus.FORBIDDEN
        )
    review.delete()
    return JsonResponse({'status': True}, status=HTTPStatus.NO_CONTENT)
