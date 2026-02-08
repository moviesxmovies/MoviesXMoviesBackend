import factory

from ratings.models import Rating

from .movies import MovieFactory
from .users import UserFactory


class RatingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Rating
        django_get_or_create = ('user', 'movie')

    rating = factory.Faker('random_int', min=Rating.MIN_RATING, max=Rating.MAX_RATING)

    user = factory.SubFactory(UserFactory)
    movie = factory.SubFactory(MovieFactory)
