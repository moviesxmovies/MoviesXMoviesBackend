from .awards import AwardFactory
from .genres import GenreFactory
from .movies import MovieFactory
from .persons import PersonFactory
from .platforms import PlatformFactory
from .ratings import RatingFactory
from .review_s import ReviewFactory
from .users import UserFactory

__all__ = [
    'UserFactory',
    'PlatformFactory',
    'AwardFactory',
    'GenreFactory',
    'PersonFactory',
    'MovieFactory',
    'RatingFactory',
    'ReviewFactory',
]
