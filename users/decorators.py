from http import HTTPStatus

import jwt
from django.conf import settings
from django.http import JsonResponse

from users.models import User

ACCESS_TYPE = 'access'


def auth_required(func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        try:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                if payload.get('token_type', '') != ACCESS_TYPE:
                    return JsonResponse(
                        {'error': 'Token type is invalid'}, status=HTTPStatus.BAD_REQUEST
                    )
                try:
                    request.user = User.objects.get(pk=payload.get('user_id'))
                except User.DoesNotExist:
                    return JsonResponse(
                        {'error': 'Token is invalid'}, status=HTTPStatus.UNAUTHORIZED
                    )

                return func(request, *args, **kwargs)
            return JsonResponse({'error': 'You need to be authenticated'}, status=HTTPStatus.UNAUTHORIZED)

        except jwt.exceptions.DecodeError:
            return JsonResponse(
                {'error': 'Token is invalid or have an incorrect padding'},
                status=HTTPStatus.BAD_REQUEST,
            )
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=HTTPStatus.BAD_REQUEST)

    return wrapper
