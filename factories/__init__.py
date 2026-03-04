from .awards import AwardFactory
from .genres import GenreFactory, GenreTranslationFactory
from .movies import MovieFactory, MovieTranslationFactory
from .persons import PersonFactory
from .platforms import PlatformFactory
from .ratings import RatingFactory
from .reviews import ReviewFactory
from .users import UserFactory
from .movielists import MovieListFactory


__all__ = [
    'UserFactory',
    'PlatformFactory',
    'AwardFactory',
    'GenreFactory',
    'PersonFactory',
    'MovieFactory',
    'RatingFactory',
    'ReviewFactory',
    'MovieListFactory',
    'MovieTranslationFactory',
    'GenreTranslationFactory',
]
