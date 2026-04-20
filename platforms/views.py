from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view

from platforms.models import Platform
from platforms.serializers import PlatformSerializer
from shared.decorators import cached_view, require_http_methods
from users.decorators import auth_required


@extend_schema(
    responses={
        200: PlatformSerializer.get_schema(many=True),
    },
    description='Returns a list of all movie platforms.',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required()
@cached_view(
    make_key=lambda req: 'platform_list',
    timeout=60 * 60 * 24,
)
def platform_list(request):
    return PlatformSerializer(Platform.objects.all()).json_response()
