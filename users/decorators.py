from http import HTTPStatus

import jwt
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from users.models import User

ACCESS_TYPE = 'access'


def auth_required(require_verification=True):
    """Decorator that enforces JWT authentication on a view.

    Extracts the Bearer token from the ``Authorization`` header, decodes
    and validates it, resolves the corresponding ``User``, and attaches it
    to ``request.user`` before delegating to the wrapped view.

    Unverified users are only permitted to access ``verify_user`` and
    ``resend_verification_email`` endpoints.

    Args:
        func (Callable): The view function to protect.

    Returns:
        Callable: The wrapped view function that performs authentication
        before calling the original view.
    """

    def _validate_token(request, token) -> JsonResponse | None:
        payload, error_response = _decode_token(token)
        if error_response:
            return error_response
        if payload.get('token_type', '') != ACCESS_TYPE:
            return JsonResponse(
                {'error': _('Token type is invalid')}, status=HTTPStatus.BAD_REQUEST
            )
        try:
            request.user = User.objects.get(pk=payload.get('user_id'))
        except User.DoesNotExist:
            return JsonResponse({'error': _('Token is invalid')}, status=HTTPStatus.UNAUTHORIZED)
        return None

    def _check_verification(request) -> JsonResponse | None:
        """Return an error response if the user is unverified and verification is required."""
        unverified_restricted_path = request.path not in [
            reverse('verify_user'),
            reverse('resend_verification_email'),
        ]
        if require_verification and not request.user.verified and unverified_restricted_path:
            return JsonResponse(
                {'error': _('User account is not verified')}, status=HTTPStatus.UNAUTHORIZED
            )
        return None

    def _decode_token(token):
        """Decode the JWT and return (payload, None) or (None, error_response)."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload, None
        except jwt.exceptions.DecodeError:
            return None, JsonResponse(
                {'error': _('Token is invalid or has incorrect padding')},
                status=HTTPStatus.BAD_REQUEST,
            )
        except jwt.ExpiredSignatureError:
            return None, JsonResponse(
                {'error': _('Token has expired')}, status=HTTPStatus.BAD_REQUEST
            )

    def decorator(func):

        def wrapper(request, *args, **kwargs):
            """Validate the JWT token and attach the resolved user to the request.

            Args:
                request: The incoming HTTP request. Must include an
                    ``Authorization: Bearer <token>`` header.
                *args: Positional arguments forwarded to the wrapped view.
                **kwargs: Keyword arguments forwarded to the wrapped view.

            Returns:
                JsonResponse: A JSON error body with HTTP 400 if the token is
                missing, malformed, or of an invalid type; HTTP 401 if the user
                does not exist, the account is unverified, or no token is
                provided; otherwise the response from the wrapped view.
            """
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse(
                    {'error': _('You need to be authenticated')}, status=HTTPStatus.UNAUTHORIZED
                )
            token = auth_header.split(' ')[1]
            if error_response := _validate_token(request, token):
                return error_response
            if error_response := _check_verification(request):
                return error_response
            previous_language = translation.get_language()
            if hasattr(request.user, 'preferred_language') and request.user.preferred_language:
                translation.activate(request.user.preferred_language)
                request.LANGUAGE_CODE = request.user.preferred_language
            try:
                return func(request, *args, **kwargs)
            finally:
                if previous_language:
                    translation.activate(previous_language)
                else:
                    translation.deactivate()

        return wrapper

    return decorator
