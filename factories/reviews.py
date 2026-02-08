import factory

from reviews.models import Review

from .movies import MovieFactory
from .users import UserFactory


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review
        django_get_or_create = ('user', 'movie')

    title = factory.Faker('sentence', nb_words=6)
    content = factory.Faker('paragraph', nb_sentences=4)
    isPositive = factory.Faker('boolean', chance_of_getting_true=70)

    user = factory.SubFactory(UserFactory)
    movie = factory.SubFactory(MovieFactory)
