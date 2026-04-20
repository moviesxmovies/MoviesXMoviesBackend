from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view

from awards.models import Award
from awards.serializers import AwardSerializer
from shared.decorators import cached_view
from users.decorators import auth_required


@extend_schema(
    responses={
        200: AwardSerializer.get_schema(),
        404: OpenApiResponse(description='Award not found.'),
    },
)
@api_view(['GET'])
@auth_required()
@cached_view(lambda req, award: f'award_detail:{award.pk}', timeout=60 * 60 * 24)
def award_detail(request, award: Award):
    return AwardSerializer(award, request=request).json_response()
