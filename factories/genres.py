import factory
from django.utils.text import slugify

from genres.models import Genre


class GenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Genre
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Genre {n}')

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.name)
