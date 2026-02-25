from movies.models import Movie
from movies.serializers import MovieSerializer
from shared.decorators import require_http_methods
from users.decorators import auth_required
from rest_framework.decorators import api_view


@api_view(['GET'])
@require_http_methods(['GET'])
@auth_required
def movie_detail(request, movie: Movie):
    return MovieSerializer(movie, request=request).json_response()
