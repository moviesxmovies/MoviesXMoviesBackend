import factory
from django.utils.text import slugify

from genres.models import Genre
from main import settings


class GenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Genre
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Genre {n}')

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.name)
    
    @factory.post_generation
    def translations(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        for translation in extracted:
            translation.genre = self
            translation.save()
        self.save(update_fields=['slug'])


class GenreTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Genre.GenreTranslation
        django_get_or_create = ('genre', 'language')

    language = factory.Iterator(settings.SUPPORTED_LANGUAGES)
    name = factory.Sequence(lambda n: f'Genre Translation {n}')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class(*args, **kwargs)