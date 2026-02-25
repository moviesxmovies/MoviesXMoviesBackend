

from shared.utils import get_object_or_json_404

from .models import MovieList


class MovieListConverter:
    regex = r'[\w-]+'

    def to_python(self, movie_list_slug: str) -> MovieList:
        return get_object_or_json_404(MovieList, slug=movie_list_slug)

    def to_url(self, movie_list: MovieList) -> str:

        return movie_list.slug
