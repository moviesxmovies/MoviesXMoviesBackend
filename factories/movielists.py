import factory

from movielists.models import MovieList

from .movies import MovieFactory
from .users import UserFactory


class MovieListFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MovieList

    name = factory.Faker('sentence', nb_words=3)

    @factory.lazy_attribute
    def slug(self):
        return self.name.lower().replace(' ', '-')

    description = factory.Faker('paragraph')
    privacity = factory.Iterator(MovieList.Privacity.values)
    user = factory.SubFactory(UserFactory)

    @factory.post_generation
    def movies(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.movies.add(*extracted)
        else:
            self.movies.add(MovieFactory(), MovieFactory())
