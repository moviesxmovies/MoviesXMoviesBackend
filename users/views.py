from http import HTTPStatus

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view

from shared.decorators import get_body, require_http_methods
from users.decorators import auth_required


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
