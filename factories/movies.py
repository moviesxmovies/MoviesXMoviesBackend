# movies/factories/movie_factory.py
import factory
from django.utils.text import slugify

from movies.models import Movie

from .awards import AwardFactory
from .genres import GenreFactory
from .persons import PersonFactory
from .platforms import PlatformFactory


class MovieFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Movie

    title = factory.Faker('sentence', nb_words=3)
    synopsis = factory.Faker('paragraph', nb_sentences=5)
    release_date = factory.Faker('date_this_century')
    cover = factory.django.ImageField(color='blue', width=300, height=450)

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.title)

    @factory.post_generation
    def directors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.directors.add(*extracted)
        else:
            self.directors.add(PersonFactory())

    @factory.post_generation
    def actors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.actors.add(*extracted)
        else:
            self.actors.add(PersonFactory(), PersonFactory())

    @factory.post_generation
    def genres(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.genres.add(*extracted)
        else:
            self.genres.add(GenreFactory())

    @factory.post_generation
    def platforms(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.platforms.add(*extracted)
        else:
            self.platforms.add(PlatformFactory())

    @factory.post_generation
    def awards(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.awards.add(*extracted)
        else:
            self.awards.add(AwardFactory())
