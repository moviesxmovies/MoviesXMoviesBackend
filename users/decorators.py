from http import HTTPStatus
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from users.models import User
from django.utils.translation import gettext as _

ACCESS_TYPE = 'access'


def auth_required(func):
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
        try:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                if payload.get('token_type', '') != ACCESS_TYPE:
                    return JsonResponse(
                        {'error': _('Token type is invalid')}, status=HTTPStatus.BAD_REQUEST
                    )
                try:
                    request.user = User.objects.get(pk=payload.get('user_id'))
                except User.DoesNotExist:
                    return JsonResponse(
                        {'error': _('Token is invalid')}, status=HTTPStatus.UNAUTHORIZED
                    )
                if not request.user.verified and request.path not in [
                    reverse('verify_user'),
                    reverse('resend_verification_email'),
                ]:
                    return JsonResponse(
                        {'error': _('User account is not verified')}, status=HTTPStatus.UNAUTHORIZED
                    )
                return func(request, *args, **kwargs)
            return JsonResponse(
                {'error': _('You need to be authenticated')}, status=HTTPStatus.UNAUTHORIZED
            )
        except jwt.exceptions.DecodeError:
            return JsonResponse(
                {'error': _('Token is invalid or has incorrect padding')},
                status=HTTPStatus.BAD_REQUEST,
            )
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': _('Token has expired')}, status=HTTPStatus.BAD_REQUEST)

    return wrapper
