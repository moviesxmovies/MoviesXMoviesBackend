from http import HTTPStatus

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.forms import ValidationError
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from reviews.serializers import ReviewSerializer
from shared.decorators import get_body, get_query_params, require_http_methods
from shared.utils import get_paginated_response
from users.decorators import auth_required
from users.models import User
from users.serializers import UserSerializer
from users.tasks import send_password_reset_email, send_verification_email

EMAIL_HELPER = 'User email'
USERNAME_HELPER = 'User username'
FIRST_NAME_HELPER = 'User first name'
LAST_NAME_HELPER = 'User last name'
USER_PASSWORD_HELPER = 'User password'


class VerifyUserSerializer(serializers.Serializer):
    verification_code = serializers.CharField(required=True, help_text='Verification code')


class FollowResponse(serializers.Serializer):
    following = serializers.BooleanField(
        help_text='Indicates if the authenticated user is following the target user'
    )


class SignupUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text=EMAIL_HELPER)
    username = serializers.CharField(required=True, help_text=USERNAME_HELPER)
    first_name = serializers.CharField(required=True, help_text=FIRST_NAME_HELPER)
    last_name = serializers.CharField(required=True, help_text=LAST_NAME_HELPER)
    password = serializers.CharField(required=True, help_text=USER_PASSWORD_HELPER)


class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, help_text=EMAIL_HELPER)
    username = serializers.CharField(required=False, help_text=USERNAME_HELPER)
    first_name = serializers.CharField(required=False, help_text=FIRST_NAME_HELPER)
    last_name = serializers.CharField(required=False, help_text=LAST_NAME_HELPER)
    password = serializers.CharField(required=False, help_text=USER_PASSWORD_HELPER)
    picture = serializers.ImageField(required=False, help_text='User profile picture')
    bio = serializers.CharField(required=False, help_text='User bio', allow_blank=True)


class ForgotPasswordResponse(serializers.Serializer):
    status = serializers.CharField(
        help_text='Status message indicating the result of the forgot password request'
    )


class ForgotPasswordValidationSerializer(serializers.Serializer):
    forgot_password_code = serializers.CharField(required=True, help_text='Forgot password code')
    new_password = serializers.CharField(required=True, help_text='New password')
    email = serializers.EmailField(required=True, help_text='User email')


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
    responses={200: UserSerializer.get_paginated_schema(), 400: None, 404: None},
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


@extend_schema(
    responses={200: UserSerializer.get_schema(), 400: None, 404: None},
    description='Retrieve the details of the authenticated user',
    methods=['GET'],
    operation_id='get_self_user_detail',
)
@extend_schema(
    request=UserUpdateSerializer,
    responses={200: UserSerializer.get_schema(), 400: None, 404: None},
    description='Update the details of the authenticated user',
    methods=['PUT'],
    operation_id='update_self_user',
)
@api_view(['GET', 'PUT'])
@require_http_methods(['GET', 'PUT'])
@auth_required
def self_user_wrapper(request):
    match request.method:
        case 'GET':
            return self_user_detail(request)
        case 'PUT':
            return update_user(request, request.user)


@require_http_methods(['GET'])
def self_user_detail(request):
    return UserSerializer(request.user, request=request).json_response()


@require_http_methods(['PUT'])
def update_user(request, user):
    data = request.data
    for field in [
        'username',
        'first_name',
        'last_name',
        'picture',
        'bio',
    ]:
        if (
            field in data
            and getattr(user, field) != data[field]
            and data[field] is not None
            and data[field].strip() != ''
        ):
            setattr(user, field, data[field])
    if 'password' in data:
        raw_password = data['password']
        try:
            validate_password(raw_password, user=user)
            user.set_password(raw_password)
        except ValidationError as e:
            errors = getattr(e, 'message_dict', {'error': e.messages})
            return JsonResponse(errors, status=HTTPStatus.BAD_REQUEST)
    if 'email' in data and user.email != data['email']:
        user.email = data['email']
        user.verified = False
        send_verification_email.delay(user)
    try:
        user.full_clean()
        user.save()
        return UserSerializer(user, request=request).json_response()
    except ValidationError as e:
        errors = getattr(e, 'message_dict', {'error': e.messages})
        return JsonResponse(errors, status=HTTPStatus.BAD_REQUEST)


@extend_schema(
    responses={200: ForgotPasswordResponse, 404: None},
    description='Initiate the forgot password process for a user account',
    methods=['GET'],
    parameters=[
        OpenApiParameter(name='email', description='Email of the user to reset password for')
    ],
)
@extend_schema(
    responses={200: bool, 400: None},
    description='Validate the forgot password code for a user account',
    methods=['POST'],
    request=ForgotPasswordValidationSerializer,
)
@api_view(['POST', 'GET'])
@require_http_methods(['POST', 'GET'])
def forgot_password_wrapper(request):
    print(f'Handling forgot password request with method: {request.method}')
    match request.method:
        case 'GET':
            return forgot_password(request)
        case 'POST':
            return forgot_password_validation(request)


@require_http_methods(['GET'])
@get_query_params('email')
def forgot_password(request, email):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=HTTPStatus.NOT_FOUND)
    send_password_reset_email.delay(user)
    return JsonResponse({'status': 'Password reset email sent'})


@require_http_methods(['POST'])
@get_body(None, ['forgot_password_code', 'new_password', 'email'])
def forgot_password_validation(request, body):
    try:
        user = User.objects.get(email=body['email'])
        if user.forgot_password_code != body['forgot_password_code']:
            return JsonResponse(
                {'error': 'Invalid verification code'}, status=HTTPStatus.BAD_REQUEST
            )
        validate_password(body['new_password'], user=user)
        user.set_password(body['new_password'])
        user.password_reset_code = None
        user.save()
        return JsonResponse({'status': 'Password reset successful'})
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid verification code'}, status=HTTPStatus.BAD_REQUEST)
    except ValidationError as e:
        errors = getattr(e, 'message_dict', {'error': e.messages})
        return JsonResponse(errors, status=HTTPStatus.BAD_REQUEST)


@extend_schema(
    responses={200: UserSerializer.get_schema(), 400: None, 404: None},
    description='Retrieve the details of a specific user by their identifier',
    operation_id='get_user_detail',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
def user_detail(request, user):
    return UserSerializer(user, request=request).json_response()


@extend_schema(
    responses={200: UserSerializer.get_schema(), 400: None, 404: None},
    description='Signup a user',
    request=SignupUserSerializer,
)
@api_view(['POST'])
@require_http_methods(['POST'])
@get_body(User, ['email', 'username', 'first_name', 'last_name', 'password'])
def user_signup(request, user: User):
    try:
        raw_password = user.password
        user.full_clean()
        validate_password(raw_password, user=user)
        user.set_password(raw_password)
        user.save()
        return UserSerializer(user, request=request).json_response()
    except ValidationError as e:
        errors = getattr(e, 'message_dict', {'error': e.messages})
        return JsonResponse(errors, status=HTTPStatus.BAD_REQUEST)


# REVIEWS
@extend_schema(
    responses={200: ReviewSerializer.get_paginated_schema(), 400: None, 404: None},
    description='Get paginated reviews of a specific user',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit')
def user_reviews(request, user: User, page: int = 1, limit: int = 10):
    reviews_query = user.reviews.order_by('-created_at')
    return get_paginated_response(reviews_query, ReviewSerializer, request, page, limit)


# FOLLOW
@extend_schema(
    responses={200: FollowResponse, 400: None, 404: None},
    methods=['POST'],
    description='Follow a user',
)
@extend_schema(
    responses={200: FollowResponse, 400: None, 404: None},
    methods=['DELETE'],
    description='Unfollow a user',
)
@api_view(['POST', 'DELETE'])
@require_http_methods(['POST', 'DELETE'])
@auth_required
def follow_user_wrapper(request, user: User):
    if request.method == 'POST':
        request.user.follow(user)
        return JsonResponse({'following': request.user.is_following(user)})
    else:
        request.user.unfollow(user)
        return JsonResponse({'following': request.user.is_following(user)})
