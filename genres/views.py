from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view

from genres.models import Genre
from genres.serializers import GenreSerializer
from shared.decorators import cached_view, require_http_methods
from users.decorators import auth_required


@extend_schema(
    responses={
        200: GenreSerializer.get_schema(many=True),
    },
    description='Returns a list of all movie genres.',
)
@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required()
@cached_view(
    make_key=lambda req: f'genre_list:{req.user.preferred_language}',
    timeout=60 * 60 * 24,
)
def genre_list(request):
    return GenreSerializer(Genre.objects.all(), request=request).json_response()
