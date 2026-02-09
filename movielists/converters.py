from http import HTTPStatus

from django.http import JsonResponse

from .models import MovieList


class MovieListConverter:
    regex = r'[\d]+'

    def to_python(self, movie_list_pk: int) -> MovieList:
        try:
            return MovieList.objects.get(pk=movie_list_pk)
        except MovieList.DoesNotExist:
            return JsonResponse({'error': 'Movie List not found'}, status=HTTPStatus.NOT_FOUND)

    def to_url(self, movie_list: MovieList) -> int:

        return movie_list.pk
