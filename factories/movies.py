# movies/factories/movie_factory.py
import factory
from django.utils.text import slugify

from main import settings
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

    @factory.post_generation
    def translations(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        for translation in extracted:
            translation.movie = self
            translation.save()
        first = extracted[0]
        self.slug = slugify(first.title)
        self.save(update_fields=['slug'])


class MovieTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Movie.MovieTranslation
        exclude = ['_save']

    language = factory.Iterator(settings.SUPPORTED_LANGUAGES)
    title = factory.Faker('sentence', nb_words=3)
    synopsis = factory.Faker('paragraph', nb_sentences=5)
    image = factory.django.ImageField(color='red', width=300, height=450)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class(*args, **kwargs)
