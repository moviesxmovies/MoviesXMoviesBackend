import logging
from datetime import datetime
from http import HTTPStatus

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.forms import ValidationError
from django.http import JsonResponse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from main import settings
from reviews.serializers import ReviewSerializer
from shared.decorators import cached_view, get_body, get_query_params, require_http_methods
from shared.utils import activate_request_language, deactivate_language, get_paginated_response
from users.decorators import auth_required
from users.models import FriendRequest, Q, User
from users.serializers import FriendRequestSerializer, UserSerializer
from users.tasks import send_password_reset_email, send_verification_email

EMAIL_HELPER = 'User email'
USERNAME_HELPER = 'User username'
FIRST_NAME_HELPER = 'User first name'
LAST_NAME_HELPER = 'User last name'
USER_PASSWORD_HELPER = 'User password'

logger = logging.getLogger(__name__)


class VerifyUserSerializer(serializers.Serializer):
    """Serializer for validating account verification payloads.

    Attributes:
        verification_code (serializers.CharField): The verification code
            sent to the user via email.
    """

    verification_code = serializers.CharField(required=True, help_text='Verification code')


class FriendResponse(serializers.Serializer):
    """Serializer for the friend request response payload.

    Attributes:
        is_friend (serializers.BooleanField): Whether the authenticated user
            is currently friends with the target user.
    """

    status = serializers.CharField(
        help_text='Request status indicating the result of the friend request action, e.g. "Friend request sent", "Unfriended", "Already friends", etc.'
    )


class SignupUserSerializer(serializers.Serializer):
    """Serializer for validating user signup payloads.

    Attributes:
        email (serializers.EmailField): User email address.
        username (serializers.CharField): Desired username.
        first_name (serializers.CharField): User first name.
        last_name (serializers.CharField): User last name.
        password (serializers.CharField): Desired password.
    """

    email = serializers.EmailField(required=True, help_text=EMAIL_HELPER)
    username = serializers.CharField(required=True, help_text=USERNAME_HELPER)
    first_name = serializers.CharField(required=True, help_text=FIRST_NAME_HELPER)
    last_name = serializers.CharField(required=True, help_text=LAST_NAME_HELPER)
    password = serializers.CharField(required=True, help_text=USER_PASSWORD_HELPER)
    picture = serializers.ImageField(required=False, help_text='User profile picture')
    bio = serializers.CharField(required=False, help_text='User bio', allow_blank=True)


class UserUpdateSerializer(serializers.Serializer):
    """Serializer for validating user profile update payloads.

    All fields are optional; only provided fields are updated.

    Attributes:
        email (serializers.EmailField): Updated email address.
        username (serializers.CharField): Updated username.
        first_name (serializers.CharField): Updated first name.
        last_name (serializers.CharField): Updated last name.
        password (serializers.CharField): Updated password.
        picture (serializers.ImageField): Updated profile picture.
        bio (serializers.CharField): Updated user bio.
    """

    email = serializers.EmailField(required=False, help_text=EMAIL_HELPER)
    username = serializers.CharField(required=False, help_text=USERNAME_HELPER)
    first_name = serializers.CharField(required=False, help_text=FIRST_NAME_HELPER)
    last_name = serializers.CharField(required=False, help_text=LAST_NAME_HELPER)
    password = serializers.CharField(required=False, help_text=USER_PASSWORD_HELPER)
    picture = serializers.ImageField(required=False, help_text='User profile picture')
    bio = serializers.CharField(required=False, help_text='User bio', allow_blank=True)


class ForgotPasswordResponse(serializers.Serializer):
    """Serializer for the forgot password initiation response.

    Attributes:
        status (serializers.BooleanField): Whether the reset email was sent.
    """

    status = serializers.BooleanField(
        help_text='Status message indicating the result of the forgot password request'
    )


class ForgotPasswordValidationSerializer(serializers.Serializer):
    """Serializer for validating forgot password confirmation payloads.

    Attributes:
        forgot_password_code (serializers.CharField): The reset code sent
            to the user via email.
        new_password (serializers.CharField): The desired new password.
        email (serializers.EmailField): The user's email address.
    """

    forgot_password_code = serializers.CharField(required=True, help_text='Forgot password code')
    new_password = serializers.CharField(required=True, help_text='New password')
    email = serializers.EmailField(required=True, help_text='User email')


class ChangePreferredLanguageSerializer(serializers.Serializer):
    """Serializer for validating preferred language change payloads.

    Attributes:
        preferred_language (serializers.ChoiceField): A language code from
            ``settings.SUPPORTED_LANGUAGES``.
    """

    preferred_language = serializers.ChoiceField(
        choices=settings.SUPPORTED_LANGUAGES, help_text='Preferred language code'
    )


class ChangePreferredLanguageResponse(serializers.Serializer):
    """Serializer for the preferred language change response.

    Attributes:
        status (serializers.BooleanField): Whether the language was updated.
    """

    status = serializers.BooleanField(
        help_text='Status message indicating the result of the change preferred language request'
    )


class GetPreferredLanguageResponse(serializers.Serializer):
    """Serializer for the get preferred language response.

    Attributes:
        preferred_language (serializers.CharField): The user's current preferred language code.
    """

    preferred_language = serializers.CharField(help_text='Current preferred language code')


@extend_schema(
    request=VerifyUserSerializer,
    responses={200: None, 400: None},
    description='Verify an user account by a code sent via email',
)
@api_view(['POST'])
@require_http_methods(['POST'])
@auth_required
@get_body(None, ['verification_code'])
def verify_user(request, body: dict) -> JsonResponse:
    """Verify the authenticated user's account using a code sent via email.

    If the user is already verified, returns success immediately. Otherwise
    compares the submitted code against the stored verification code.

    Args:
        request: The authenticated incoming HTTP request.
        body (dict): Parsed request body containing ``'verification_code'``,
            injected by ``get_body``.

    Returns:
        JsonResponse: ``{'status': True}`` with HTTP 200 on success, or a
        JSON error body with HTTP 400 if the code is incorrect.
    """
    user = request.user
    if user.verified:
        return JsonResponse({'status': True})

    if user.verification_code == body['verification_code']:
        user.verified = True
        user.save()
        return JsonResponse({'status': True})

    return JsonResponse(
        {'error': _('Verification code is incorrect')}, status=HTTPStatus.BAD_REQUEST
    )


@extend_schema(
    responses={200: None, 429: None},
    description='Verify an user account by a code sent via email',
)
@api_view(['POST'])
@require_http_methods(['POST'])
@auth_required
def resend_verification_email(request) -> JsonResponse:
    """Resend the verification email to the authenticated user.

    Enforces a 60-second cooldown per user using the Django cache. If the
    user is already verified, returns success without sending an email.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: ``{'status': 'User is already verified'}`` if already
        verified, a JSON error body with HTTP 429 if the cooldown is active,
        or ``{'status': 'Verification email resent'}`` with HTTP 200 on success.
    """
    user = request.user
    if user.verified:
        return JsonResponse({'status': _('User is already verified')})
    cache_key = f'resend_verification_cooldown_{user.id}'
    remaining_time = cache.ttl(cache_key)
    if remaining_time > 0:
        return JsonResponse(
            {
                'error': _(
                    'You can resend the verification email in {remaining_time} seconds'
                ).format(remaining_time=remaining_time)
            },
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )
    send_verification_email.delay(user)
    cache.set(cache_key, True, timeout=60)
    return JsonResponse({'status': _('Verification email resent')})


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
@cached_view(
    make_key=lambda req, page=1, limit=10: f'suggested_users:{req.user.pk}:{page}:{limit}',
    timeout=60 * 15,
)
def suggested_users(request, page: int, limit: int) -> JsonResponse:
    """Return a paginated list of suggested users for the authenticated user to follow.

    Suggestions are generated by ``request.user.suggest_friends()``.

    Args:
        request: The authenticated incoming HTTP request.
        page (int): Page number for pagination, injected by ``get_query_params``.
        limit (int): Number of items per page, injected by ``get_query_params``.

    Returns:
        JsonResponse: Paginated serialized user list with HTTP 200.
    """
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
    request={
        'multipart/form-data': UserUpdateSerializer,
    },
    responses={200: UserSerializer.get_schema(), 400: None, 404: None},
    description='Update the details of the authenticated user',
    methods=['PUT'],
    operation_id='update_self_user',
)
@api_view(['GET', 'PUT'])
@require_http_methods(['GET', 'PUT'])
@auth_required
def self_user_wrapper(request) -> JsonResponse:
    """Route GET and PUT requests for the authenticated user's own profile.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: The response from ``self_user_detail`` on GET,
        or from ``update_user`` on PUT.
    """
    match request.method:
        case 'GET':
            return self_user_detail(request)
        case 'PUT':
            return update_user(request, request.user)


@require_http_methods(['GET'])
@cached_view(lambda req: f'self_user_detail:{req.user.pk}', timeout=60 * 60)
def self_user_detail(request) -> JsonResponse:
    """Return the serialized profile of the authenticated user.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: Serialized user data with HTTP 200.
    """
    return UserSerializer(request.user, request=request).json_response()


@require_http_methods(['PUT'])
def update_user(request, user: User) -> JsonResponse:
    """Apply partial updates to a user profile and persist the changes.

    Updates only the fields present in ``request.data`` that differ from
    the current values. Handles password hashing, email verification reset,
    and model-level validation via ``full_clean()``.

    Args:
        request: The authenticated incoming HTTP request. ``request.data``
            may contain any subset of fields defined in ``UserUpdateSerializer``.
        user (User): The user instance to update.

    Returns:
        JsonResponse: Serialized updated user with HTTP 200, or a JSON error
        body with HTTP 400 on validation failure.
    """
    data = request.data
    for field in [
        'username',
        'first_name',
        'last_name',
        'bio',
    ]:
        if (
            field in data
            and getattr(user, field) != data[field]
            and data[field] is not None
            and data[field] != ''
        ):
            setattr(user, field, data[field])

    if 'password' in data and data['password'] != '':
        raw_password = data['password']
        try:
            validate_password(raw_password, user=user)
            user.set_password(raw_password)
        except ValidationError as e:
            errors = getattr(e, 'message_dict', {'error': e.messages})
            return JsonResponse(errors, status=HTTPStatus.BAD_REQUEST)

    if 'email' in data and data['email'] != '' and user.email != data['email']:
        user.email = data['email']
        user.verified = False
        send_verification_email.delay(user)

    try:
        picture = request.FILES.get('picture')
        if picture:
            picture.name = f'user_{user.username}_profile_{datetime.now().strftime("%Y%m%d%H%M%S")}.{picture.name.split(".")[-1]}'
            user.picture = picture
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
        OpenApiParameter(
            name='email', required=True, description='Email of the user to reset password for'
        ),
        OpenApiParameter(name='lang', required=False, description='User lang preference'),
    ],
)
@extend_schema(
    responses={200: bool, 400: None},
    description='Validate the forgot password code for a user account',
    methods=['POST'],
    request=ForgotPasswordValidationSerializer,
    parameters=[OpenApiParameter(name='lang', required=False, description='User lang preference')],
)
@api_view(['POST', 'GET'])
@require_http_methods(['POST', 'GET'])
def forgot_password_wrapper(request) -> JsonResponse:
    """Route GET and POST forgot-password requests to their respective handlers.

    Args:
        request: The incoming HTTP request. No authentication required.

    Returns:
        JsonResponse: The response from ``forgot_password`` on GET,
        or from ``forgot_password_validation`` on POST.
    """
    previous_language = activate_request_language(request)
    try:
        match request.method:
            case 'GET':
                return forgot_password(request)
            case 'POST':
                return forgot_password_validation(request)
    finally:
        deactivate_language(previous_language)


@require_http_methods(['GET'])
@get_query_params('email')
def forgot_password(request, email: str) -> JsonResponse:
    """Initiate the password reset flow by sending a reset email.

    Looks up the user by email and dispatches a password reset email
    asynchronously via Celery.

    Args:
        request: The incoming HTTP request.
        email (str): The email address to look up, injected by
            ``get_query_params``.

    Returns:
        JsonResponse: ``{'status': 'Password reset email sent'}`` with HTTP 200,
        or a JSON error body with HTTP 404 if no user matches the email.
    """
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': _('User not found')}, status=HTTPStatus.NOT_FOUND)
    cache_key = f'resend_forgot_password_cooldown_{user.id}'
    remaining_time = cache.ttl(cache_key)
    if remaining_time > 0:
        return JsonResponse(
            {
                'error': _(
                    'You can resend the password reset email in {remaining_time} seconds'
                ).format(remaining_time=remaining_time)
            },
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )
    send_password_reset_email.delay(user)
    cache.set(cache_key, True, timeout=60)
    return JsonResponse({'status': _('Password reset email sent')})


@require_http_methods(['POST'])
@get_body(None, ['forgot_password_code', 'new_password', 'email'])
def forgot_password_validation(request, body: dict) -> JsonResponse:
    """Validate a password reset code and apply the new password.

    Looks up the user by email, verifies the reset code, validates the new
    password via Django's password validators, and persists the change.

    Args:
        request: The incoming HTTP request.
        body (dict): Parsed request body containing ``'forgot_password_code'``,
            ``'new_password'``, and ``'email'``, injected by ``get_body``.

    Returns:
        JsonResponse: ``{'status': 'Password reset successful'}`` with HTTP 200,
        or a JSON error body with HTTP 400 on invalid code or validation failure,
        or HTTP 400 if the user is not found.
    """
    try:
        user = User.objects.get(email=body['email'])
        if user.forgot_password_code != body['forgot_password_code']:
            return JsonResponse(
                {'error': _('Invalid verification code')}, status=HTTPStatus.BAD_REQUEST
            )
        validate_password(body['new_password'], user=user)
        user.set_password(body['new_password'])
        user.forgot_password_code = None
        user.verified = True  # Automatically verify the user upon successful password reset
        user.verification_code = None
        user.save()
        return JsonResponse({'status': _('Password reset successful')})
    except User.DoesNotExist:
        return JsonResponse(
            {'error': _('Invalid verification code')}, status=HTTPStatus.BAD_REQUEST
        )
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
@cached_view(make_key=lambda req, user: f'user_detail:{user.pk}', timeout=60 * 60)
def user_detail(request, user: User) -> JsonResponse:
    """Return the serialized profile of a specific user.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user instance resolved from the URL.

    Returns:
        JsonResponse: Serialized user data with HTTP 200.
    """
    return UserSerializer(user, request=request).json_response()


@extend_schema(
    responses={200: UserSerializer.get_schema(), 400: None, 404: None},
    description='Signup a user',
    request={
        'multipart/form-data': SignupUserSerializer,
    },
    parameters=[
        OpenApiParameter(
            name='lang',
            description='User preferred language',
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        )
    ],
)
@api_view(['POST'])
@require_http_methods(['POST'])
def user_signup(request) -> JsonResponse:
    """Create and persist a new user account.

    Runs model-level validation via ``full_clean()``, validates the password
    via Django's password validators, hashes it, and saves the new user.

    Args:
        request: The incoming HTTP request.
        user (User): Unsaved ``User`` instance constructed from the request
            body by ``get_body``.

    Returns:
        JsonResponse: Serialized new user with HTTP 200, or a JSON error
        body with HTTP 400 on validation failure.
    """
    previous_language = translation.get_language()
    try:
        preferred_language = request.GET.get('lang', settings.DEFAULT_LANGUAGE)
        if preferred_language not in settings.SUPPORTED_LANGUAGES:
            preferred_language = settings.DEFAULT_LANGUAGE
        translation.activate(preferred_language)

        for field in ['username', 'email', 'first_name', 'last_name', 'password']:
            if (
                field not in request.data
                or request.data[field] is None
                or request.data[field] == ''
            ):
                return JsonResponse(
                    {'error': {'error': _(f'{field} is required')}}, status=HTTPStatus.BAD_REQUEST
                )

        user = User(
            username=request.data['username'],
            email=request.data['email'],
            first_name=request.data['first_name'],
            last_name=request.data['last_name'],
            preferred_language=preferred_language,
        )
        raw_password = request.data['password']
        validate_password(raw_password, user=user)
        user.set_password(raw_password)
        user.full_clean()

        picture = request.FILES.get('picture')
        if picture:
            picture.name = f'user_{user.username}_profile_{datetime.now().strftime("%Y%m%d%H%M%S")}.{picture.name.split(".")[-1]}'
            user.picture = picture

        bio = request.data.get('bio')
        if bio is not None and bio.strip() != '':
            user.bio = bio

        user.save()
        return UserSerializer(user, request=request).json_response()

    except ValidationError as e:
        errors = getattr(e, 'message_dict', {'error': e.messages})
        return JsonResponse(errors, status=HTTPStatus.BAD_REQUEST)
    finally:
        deactivate_language(previous_language)


@extend_schema(
    responses={200: ChangePreferredLanguageResponse, 400: None, 404: None},
    description='Set preferred language for the authenticated user',
    methods=['POST'],
    request=ChangePreferredLanguageSerializer,
)
@extend_schema(
    responses={200: GetPreferredLanguageResponse, 400: None, 404: None},
    description='Get preferred language for the authenticated user',
    methods=['GET'],
)
@api_view(['POST', 'GET'])
@require_http_methods(['POST', 'GET'])
@auth_required
def preferred_language_wrapper(request) -> JsonResponse:
    """Route GET and POST requests for the authenticated user's preferred language.

    Args:
        request: The authenticated incoming HTTP request.
    Returns:
        JsonResponse: The response from ``get_preferred_language`` on GET,
        or from ``set_preferred_language`` on POST.
    """
    match request.method:
        case 'GET':
            return get_preferred_language(request)
        case 'POST':
            return set_preferred_language(request)


@require_http_methods(['GET'])
def get_preferred_language(request) -> JsonResponse:
    """Return the authenticated user's preferred language.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: ``{'preferred_language': str}`` with HTTP 200.
    """
    return JsonResponse({'preferred_language': request.user.preferred_language})


@require_http_methods(['POST'])
@get_body(None, ['preferred_language'])
def set_preferred_language(request, body: dict) -> JsonResponse:
    """Set the preferred language for the authenticated user.

    Validates the submitted language code against ``settings.SUPPORTED_LANGUAGES``
    before persisting the change.

    Args:
        request: The authenticated incoming HTTP request.
        body (dict): Parsed request body containing ``'preferred_language'``,
            injected by ``get_body``.

    Returns:
        JsonResponse: ``{'status': True}`` with HTTP 200, or a JSON error
        body with HTTP 400 if the language code is not supported.
    """
    preferred_language = body['preferred_language']
    if preferred_language not in settings.SUPPORTED_LANGUAGES:
        return JsonResponse({'error': _('Invalid language code')}, status=HTTPStatus.BAD_REQUEST)
    request.user.preferred_language = preferred_language
    request.user.save()
    return JsonResponse({'status': True})


class OnboardingResponse(serializers.Serializer):
    """Serializer for the onboarding response.

    Attributes:
        status (serializers.BooleanField): Whether the onboarding was completed.
    """

    status = serializers.BooleanField(help_text='Whether the onboarding was successfully completed')


@extend_schema(
    responses={200: OnboardingResponse, 400: None},
    description='Complete onboarding for the authenticated user by setting boarded to true',
)
@api_view(['POST'])
@require_http_methods(['POST'])
@auth_required
def complete_onboarding(request) -> JsonResponse:
    """Mark the authenticated user's onboarding as complete.

    Sets the ``boarded`` field to ``True`` for the requesting user.

    Args:
        request: The authenticated incoming HTTP request.

    Returns:
        JsonResponse: ``{'status': True}`` with HTTP 200 on success, or
        ``{'status': False}`` with HTTP 400 on failure.
    """
    try:
        user = request.user
        user.boarded = True
        user.save(update_fields=['boarded'])
        return JsonResponse({'status': True})
    except Exception:
        logger.exception('Failed to complete onboarding for user %s', request.user.pk)
        return JsonResponse({'status': False}, status=HTTPStatus.BAD_REQUEST)


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
@cached_view(
    make_key=lambda req, user, page=1, limit=10: f'user_reviews:{user.pk}:{page}:{limit}',
    timeout=60 * 5,
)
def user_reviews(request, user: User, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of reviews written by a specific user.

    Reviews are ordered by most recently created first.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user instance resolved from the URL.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized reviews with HTTP 200.
    """
    reviews_query = user.reviews.order_by('-created_at')
    return get_paginated_response(reviews_query, ReviewSerializer, request, page, limit)


# FRIENDS
def _get_friends_response(request, user: User, page: int, limit: int) -> JsonResponse:
    return get_paginated_response(user.get_friends(), UserSerializer, request, page, limit)


@extend_schema(
    responses={200: UserSerializer.get_paginated_schema(), 400: None, 404: None},
    description='Get paginated friends of a specific user',
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
    make_key=lambda req, user, page=1, limit=10: f'user_friends:{user.pk}:{page}:{limit}',
    timeout=60 * 5,
)
def user_friends(request, user: User, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of a specific user's friends.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user instance resolved from the URL.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Serialized list of friends with HTTP 200.
    """
    return _get_friends_response(request, user, page, limit)


@extend_schema(
    responses={200: UserSerializer.get_paginated_schema(), 400: None, 404: None},
    description='Get self paginated friends of the authenticated user',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit')
def self_friends(request, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of the authenticated user's friends.

    Args:
        request: The authenticated incoming HTTP request.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.

    Returns:
        JsonResponse: Paginated serialized friends with HTTP 200.
    """
    return _get_friends_response(request, request.user, page, limit)


@extend_schema(
    responses={200: FriendRequestSerializer.get_paginated_schema(), 400: None, 404: None},
    description='Get paginated friend requests for a specific user',
    parameters=[
        OpenApiParameter(name='page', description='Page number', required=False, type=int),
        OpenApiParameter(name='limit', description='Items per page', required=False, type=int),
    ],
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
@get_query_params('page', 'limit')
def self_friend_requests(request, page: int = 1, limit: int = 10) -> JsonResponse:
    """Return a paginated list of incoming friend requests for a specific user.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The user instance resolved from the URL.
        page (int): Page number for pagination. Defaults to 1.
        limit (int): Number of items per page. Defaults to 10.
    Returns:
        JsonResponse: Paginated serialized friend requests with HTTP 200.
    """
    friend_requests_query = FriendRequest.objects.filter(
        to_user=request.user, status=FriendRequest.Status.PENDING
    ).order_by('-created_at')
    return get_paginated_response(
        friend_requests_query, FriendRequestSerializer, request, page, limit
    )


@extend_schema(
    responses={200: FriendResponse, 400: FriendResponse, 404: None},
    description='Send or accept friend requests for a specific user',
    methods=['POST'],
)
@extend_schema(
    responses={200: FriendResponse, 400: FriendResponse, 404: None},
    description='Delete a friend or reject a friend request for a specific user',
    methods=['DELETE'],
)
@api_view(['POST', 'DELETE'])
@require_http_methods(['POST', 'DELETE'])
@auth_required
def friend_requests_wrapper(request, user: User) -> JsonResponse:
    match request.method:
        case 'POST':
            return save_accept_friend_request(request, user)
        case 'DELETE':
            return delete_friend_request(request, user)


@require_http_methods(['POST'])
def save_accept_friend_request(request, user: User) -> JsonResponse:
    """
    Create a new friend request or accept an incoming request between the authenticated user and the specified user.
     - If they are already friends, returns an error.
     - If there is a pending friend request from the authenticated user to the specified user, returns an error.
     - If there is a pending friend request from the specified user to the authenticated user, accepts it and establishes the friendship.
     - If there is no existing relationship, creates a new pending friend request from the authenticated user to the specified user.
     Args:
        request: The authenticated incoming HTTP request.
        user (User): The target user instance resolved from the URL.
    Returns:
        JsonResponse: A JSON response with a 'status' message indicating the result of the operation"""
    if request.user.pk == user.pk:
        return JsonResponse(
            {'status': _('You cannot friend yourself')}, status=HTTPStatus.BAD_REQUEST
        )

    if request.user.is_friend(user):
        return JsonResponse({'status': _('Already friends')}, status=HTTPStatus.BAD_REQUEST)

    existing_request = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=user) | Q(from_user=user, to_user=request.user)
    ).first()

    if existing_request is None:
        FriendRequest.objects.create(from_user=request.user, to_user=user)
        return JsonResponse({'status': _('Friend request sent')})

    if existing_request.status == FriendRequest.Status.REJECTED:
        existing_request.from_user = request.user
        existing_request.to_user = user
        existing_request.reset()
        return JsonResponse({'status': _('Friend request sent')})

    if (
        existing_request.to_user == request.user
        and existing_request.status == FriendRequest.Status.PENDING
    ):
        existing_request.accept()
        return JsonResponse({'status': _('Friend request accepted')})

    return JsonResponse({'status': _('Friend request already sent')}, status=HTTPStatus.BAD_REQUEST)


@require_http_methods(['DELETE'])
def delete_friend_request(request, user: User) -> JsonResponse:
    """Delete the friend relationship or pending friend request between the authenticated user and the specified user.

    If they are friends, deletes the friendship. If there is a pending friend request in either direction, deletes it. If there is no relationship, does nothing.

    Args:
        request: The authenticated incoming HTTP request.
        user (User): The target user instance resolved from the URL.
    Returns:
        JsonResponse: ``{'status': 'Unfriended'}`` with HTTP 200 if they were friends, ``{'status': 'Friend request deleted'}`` if a pending request was deleted, or a JSON error body with HTTP 400 if the user tries to unfriend themselves.
    """
    if request.user.pk == user.pk:
        return JsonResponse(
            {'status': _('You cannot unfriend yourself')}, status=HTTPStatus.BAD_REQUEST
        )

    friend_request = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=user, status=FriendRequest.Status.PENDING)
        | Q(from_user=user, to_user=request.user, status=FriendRequest.Status.PENDING)
    ).first()

    if friend_request is None:
        return JsonResponse(
            {'status': _('No friend relationship to reject')}, status=HTTPStatus.BAD_REQUEST
        )

    friend_request.reject()
    return JsonResponse({'status': _('Friend request rejected')})
