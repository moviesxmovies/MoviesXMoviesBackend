from http import HTTPStatus

from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from shared.decorators import get_body, get_query_params, require_http_methods
from users.decorators import auth_required
from users.serializers import UserSerializer
from users.tasks import send_verification_email


class VerifyUserSerializer(serializers.Serializer):
    verification_code = serializers.CharField(required=True, help_text='Verification code')


@extend_schema(
    request=VerifyUserSerializer,
    responses={200: None, 400: None},
    description='Verify an user account by a code sent via email',
    
)
@api_view(['POST'])
@require_http_methods(['POST'])
@auth_required
@get_body(None, ['verification_code'])
def verify_user(request, body):
    user = request.user
    if user.verified:
        return JsonResponse({'status': True})

    if user.verification_code == body['verification_code']:
        user.verified = True
        user.save()
        return JsonResponse({'status': True})

    return JsonResponse({'error': 'Verification code is incorrect'}, status=HTTPStatus.BAD_REQUEST)


@extend_schema(
    responses={200: None, 429: None},
    description='Verify an user account by a code sent via email',
)
@api_view(['POST'])
@require_http_methods(['POST'])
@auth_required
def resend_verification_email(request):
    user = request.user
    if user.verified:
        return JsonResponse({'status': 'User is already verified'})
    cache_key = f'resend_verification_cooldown_{user.id}'
    remaining_time = cache.ttl(cache_key)
    if remaining_time > 0:
        return JsonResponse(
            {'error': f'You can resend the verification email in {remaining_time} seconds'},
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )
    send_verification_email.delay(user)
    cache.set(cache_key, True, timeout=60)
    return JsonResponse({'status': 'Verification email resent'})

@extend_schema(
    responses={200: UserSerializer, 400: None, 404: None},
    description='Get a list of suggested users to follow based on mutual friends',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit')
def suggested_users(request, page, limit):
    suggested_users_query = request.user.suggest_friends()
    page = int(page) if page and page.isdigit() else 1
    limit = int(limit) if limit and limit.isdigit() else 5

    paginator = Paginator(suggested_users_query, limit)
    page_result = paginator.get_page(page)
    serialized_users = [
        UserSerializer(user, request=request).serialize() for user in page_result.object_list
    ]
    return JsonResponse(
        {
            'results': serialized_users,
            'total_pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': page_result.has_next(),
            'has_previous': page_result.has_previous(),
            'current_page': page_result.number,
        }
    )


@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
def self_user_detail(request):
    return UserSerializer(request.user, request=request).json_response()


@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
def user_detail(request, user):
    return UserSerializer(user, request=request).json_response()
