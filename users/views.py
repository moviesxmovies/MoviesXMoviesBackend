from http import HTTPStatus

from django.core.cache import cache
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from shared.decorators import get_body, get_query_params, require_http_methods
from shared.utils import get_paginated_response
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
    return get_paginated_response(
        request.user.suggest_friends(), UserSerializer, request, page, limit
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
