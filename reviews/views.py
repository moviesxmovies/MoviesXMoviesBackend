from http import HTTPStatus

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.forms import ValidationError
from django.http import JsonResponse
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from reviews.models import Comment, Reaction, Review
from reviews.serializers import (
    CommentSerializer,
    ReactionManySerializer,
    ReactionSerializer,
    ReviewSerializer,
)
from shared.decorators import get_body, get_query_params, require_http_methods
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


class SaveReactionSerializer(serializers.Serializer):
    emoji_code = serializers.ChoiceField(
        choices=Reaction.EmojiType.choices, help_text='Type of emoji'
    )


class SaveCommentSerializer(serializers.Serializer):
    content = serializers.CharField(required=True, help_text='Content of comment')


class UpdateCommentSerializer(serializers.Serializer):
    content = serializers.CharField(required=True, help_text='Updated content of comment')


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
            {'error': _('You can only edit your own reviews')}, status=HTTPStatus.FORBIDDEN
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
            {'error': _('You can only delete your own reviews')}, status=HTTPStatus.FORBIDDEN
        )
    review.delete()
    return JsonResponse({'status': True}, status=HTTPStatus.NO_CONTENT)


# COMMENTS AND REACTIONS


def _add_reaction(request, target, emoji_code) -> JsonResponse:
    """Add a reaction to a target (review or comment).

    If the requester has already reacted with the same emoji, returns bad request.
    Otherwise, a new reaction is created.

    Args:
        request: The authenticated incoming HTTP request.
        target: The review or comment instance to react to.
        emoji_code: The code of the emoji to react with.

    Returns:
        JsonResponse: A JSON object containing the status of the operation,
        or an error message if the input is invalid.
    """
    user = request.user
    try:
        reaction = Reaction(user=user, target=target, emoji=emoji_code)
        reaction.full_clean()
        reaction.save()
        return JsonResponse(
            {
                'status': True,
            }
        )
    except IntegrityError:
        return JsonResponse(
            {'error': 'You have already reacted with this emoji'}, status=HTTPStatus.BAD_REQUEST
        )
    except ValidationError as e:
        return JsonResponse({'error': e.message_dict}, status=HTTPStatus.BAD_REQUEST)


def _delete_reaction(request, reaction) -> JsonResponse:
    """Delete a reaction from a target (review or comment).
    Only the owner of the reaction may delete it.
    Args:
        request: The authenticated incoming HTTP request.
        reaction: The reaction instance to delete.
    Returns:
        JsonResponse: ``{'status': True}`` with HTTP 204 on success, or a JSON error body with HTTP 403 if the requester is not the reaction owner.
    """
    if reaction.user != request.user:
        return JsonResponse(
            {'error': _('You can only delete your own reactions')}, status=HTTPStatus.FORBIDDEN
        )
    reaction.delete()
    return JsonResponse({'status': True}, status=HTTPStatus.NO_CONTENT)


@extend_schema(
    methods=['GET'],
    responses={200: ReactionManySerializer.get_schema(), 404: None},
    description='Gets reactions of review',
    operation_id='get_review_reactions',
)
@extend_schema(
    methods=['POST'],
    responses={200: bool, 404: None},
    request=SaveReactionSerializer,
    description='Add a reaction to a review',
    operation_id='add_review_reaction',
)
@api_view(['GET', 'POST'])
@auth_required
@require_http_methods(['GET', 'POST'])
def reaction_review_wrapper(request, review: Review):
    match request.method:
        case 'GET':
            return get_review_reactions(request, review)
        case 'POST':
            return add_review_reaction(request, review)


@require_http_methods(['GET'])
def get_review_reactions(request, review: Review) -> JsonResponse:
    """Retrieve aggregated reaction counts and the requester's reactions for a review.

    Args:
        request: The authenticated incoming HTTP request.
        review (Review): The review instance resolved from the URL.
    Returns:
        JsonResponse: A JSON object containing:
            - 'reactions': A dictionary mapping emoji codes to their total counts.
            - 'your_reactions': A dictionary mapping emoji codes to the IDs of the requester's reactions.
    """
    reactions_queryset = Reaction.objects.filter(
        content_type=ContentType.objects.get_for_model(Review), object_id=review.pk
    )
    return ReactionManySerializer(reactions_queryset, request=request).json_response()


@require_http_methods(['POST'])
@get_body(None, ['emoji_code'])
def add_review_reaction(request, review: Review, body: dict) -> JsonResponse:
    """Add a reaction to a review.

    If the requester has already reacted with the same emoji, returns 400.
    Otherwise, a new reaction is created.

    Args:
        request: The authenticated incoming HTTP request.
        review (Review): The review instance resolved from the URL.
        body (dict): Parsed request body containing ``'emoji_code'``, injected by ``get_body``.

    Returns:
        JsonResponse: A JSON object containing the status of the operation,
        or an error message if the input is invalid.
    """

    return _add_reaction(request, review, body['emoji_code'])


@extend_schema(
    methods=['GET'],
    responses={200: CommentSerializer.get_progressive_pagination_schema(), 404: None},
    description='Gets comments of review',
    operation_id='get_review_comments',
    parameters=[
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
        OpenApiParameter(
            name='last_id',
            description='ID of the last item from the previous page',
            required=False,
            type=int,
        ),
    ],
)
@extend_schema(
    methods=['POST'],
    responses={201: CommentSerializer.get_schema(), 404: None},
    request=SaveCommentSerializer,
    description='Create a comment on a review',
    operation_id='create_review_comment',
)
@api_view(['GET', 'POST'])
@auth_required
@require_http_methods(['GET', 'POST'])
def comment_wrapper(request, review: Review):
    match request.method:
        case 'GET':
            return get_review_comments(request, review)
        case 'POST':
            return add_review_comment(request, review)


@require_http_methods(['GET'])
@get_query_params('limit', 'last_id')
def get_review_comments(request, review: Review, limit: int, last_id: int) -> JsonResponse:
    if limit is None:
        limit = 20
    limit = int(limit)
    queryset = Comment.objects.filter(
        review=review,
        reply_comment=None,
        **({'pk__lt': last_id} if last_id else {}),
    ).order_by('-pk')[: limit + 1]

    comments = list(queryset)
    has_more = len(comments) > limit
    if has_more:
        comments = comments[:-1]

    return JsonResponse(
        {
            'results': CommentSerializer(comments, request=request).serialize(),
            'next_last_id': comments[-1].pk if has_more else None,
        }
    )


@require_http_methods(['POST'])
@get_body(None, ['content'])
def add_review_comment(request, review: Review, body: dict) -> JsonResponse:
    comment = Comment.objects.create(user=request.user, review=review, content=body['content'])
    response = CommentSerializer(comment, request=request).json_response()
    response.status_code = HTTPStatus.CREATED
    return response


@extend_schema(
    methods=['GET'],
    responses={200: CommentSerializer.get_schema(), 404: None},
    description='Gets a comment of a review',
    operation_id='get_review_comment',
)
@extend_schema(
    methods=['PUT'],
    responses={200: CommentSerializer.get_schema(), 404: None},
    request=UpdateCommentSerializer,
    description='Edit a comment on a review',
    operation_id='edit_review_comment',
)
@extend_schema(
    methods=['DELETE'],
    responses={204: bool, 404: None},
    description='Delete a comment on a review',
    operation_id='delete_review_comment',
)
@api_view(['GET', 'PUT', 'DELETE'])
@auth_required
def comment_wrapper_with_id(request, review: Review, comment: Comment):
    match request.method:
        case 'GET':
            return get_comment(request, review, comment)
        case 'PUT':
            return update_comment(request, review, comment)
        case 'DELETE':
            return delete_comment(request, review, comment)


@require_http_methods(['GET'])
def get_comment(request, review: Review, comment: Comment) -> JsonResponse:
    return CommentSerializer(comment, request=request).json_response()


@require_http_methods(['PUT'])
@get_body(None, ['content'])
def update_comment(request, review: Review, comment: Comment, body: dict) -> JsonResponse:
    if comment.user != request.user:
        return JsonResponse(
            {'error': _('You can only edit your own comments')}, status=HTTPStatus.FORBIDDEN
        )
    comment.content = body['content']
    comment.save()
    return CommentSerializer(comment, request=request).json_response()


@require_http_methods(['DELETE'])
def delete_comment(request, review: Review, comment: Comment) -> JsonResponse:
    if comment.user != request.user:
        return JsonResponse(
            {'error': _('You can only delete your own comments')}, status=HTTPStatus.FORBIDDEN
        )
    comment.delete()
    return JsonResponse({'status': True}, status=HTTPStatus.NO_CONTENT)


@extend_schema(
    methods=['GET'],
    responses={200: ReactionManySerializer.get_schema(), 404: None},
    description='Gets reactions of a comment',
    operation_id='get_comment_reactions',
)
@extend_schema(
    methods=['POST'],
    responses={200: ReactionSerializer.get_schema(), 404: None},
    request=SaveReactionSerializer,
    description='Add a reaction to a comment',
    operation_id='add_comment_reaction',
)
@api_view(['GET', 'POST'])
@auth_required
@require_http_methods(['GET', 'POST'])
def reaction_comment_wrapper(request, review: Review, comment: Comment):
    match request.method:
        case 'GET':
            return get_comment_reactions(request, review, comment)
        case 'POST':
            return add_comment_reaction(request, review, comment)


@require_http_methods(['GET'])
def get_comment_reactions(request, review: Review, comment: Comment) -> JsonResponse:
    reactions_queryset = Reaction.objects.filter(
        content_type=ContentType.objects.get_for_model(Comment), object_id=comment.pk
    )
    return ReactionManySerializer(reactions_queryset, request=request).json_response()


@require_http_methods(['POST'])
@get_body(None, ['emoji_code'])
def add_comment_reaction(request, review: Review, comment: Comment, body: dict) -> JsonResponse:
    return _add_reaction(request, comment, body['emoji_code'])


@extend_schema(
    methods=['GET'],
    responses={200: CommentSerializer.get_progressive_pagination_schema(), 404: None},
    description='Gets replies of a comment',
    operation_id='get_comment_replies',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
        OpenApiParameter(
            name='last_id',
            description='ID of the last item from the previous page',
            required=False,
            type=int,
        ),
    ],
)
@extend_schema(
    methods=['POST'],
    responses={201: CommentSerializer.get_schema(), 404: None},
    request=SaveCommentSerializer,
    description='Create a reply to a comment',
    operation_id='create_comment_reply',
)
@api_view(['GET', 'POST'])
@auth_required
@require_http_methods(['GET', 'POST'])
def reply_wrapper(request, review: Review, comment: Comment):
    match request.method:
        case 'GET':
            return get_comment_replies(request, review, comment)
        case 'POST':
            return add_comment_reply(request, review, comment)


@require_http_methods(['GET'])
@get_query_params('limit', 'last_id')
def get_comment_replies(
    request, review: Review, comment: Comment, limit: int = 20, last_id: int = None
) -> JsonResponse:
    if limit is None:
        limit = 20
    limit = int(limit)
    queryset = Comment.objects.filter(
        review=review,
        reply_comment=comment,
        **({'pk__lt': last_id} if last_id else {}),
    ).order_by('-pk')[: limit + 1]

    comments = list(queryset)
    has_more = len(comments) > limit
    if has_more:
        comments = comments[:-1]

    return JsonResponse(
        {
            'results': CommentSerializer(comments, request=request).serialize(),
            'next_last_id': comments[-1].pk if has_more else None,
        }
    )


@require_http_methods(['POST'])
@get_body(None, ['content'])
def add_comment_reply(request, review: Review, comment: Comment, body: dict) -> JsonResponse:
    reply = Comment.objects.create(
        user=request.user, review=review, content=body['content'], reply_comment=comment
    )
    response = CommentSerializer(reply, request=request).json_response()
    response.status_code = HTTPStatus.CREATED
    return response


@extend_schema(
    methods=['DELETE'],
    responses={204: bool, 404: None},
    description='Delete a reaction from a comment',
    operation_id='delete_comment_reaction',
)
@api_view(['DELETE'])
@auth_required
@require_http_methods(['DELETE'])
def delete_reaction_comment(
    request, review: Review, comment: Comment, reaction: Reaction
) -> JsonResponse:
    return _delete_reaction(request, reaction)


@extend_schema(
    methods=['DELETE'],
    responses={204: bool, 404: None},
    description='Delete a reaction from a review',
    operation_id='delete_review_reaction',
)
@api_view(['DELETE'])
@auth_required
@require_http_methods(['DELETE'])
def delete_review_reaction(request, review: Review, reaction: Reaction) -> JsonResponse:
    return _delete_reaction(request, reaction)
