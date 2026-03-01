from shared.utils import get_object_or_json_404

from .models import Movie


class MovieConverter:
    regex = r'[\w-]+'

    def to_python(self, slug: str) -> Movie:
        return get_object_or_json_404(Movie, slug=slug)

    def to_url(self, movie: Movie) -> str:
        return movie.slug
