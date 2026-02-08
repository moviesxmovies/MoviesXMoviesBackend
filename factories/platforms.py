import factory
from django.utils.text import slugify

from platforms.models import Platform


class PlatformFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Platform
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Platform {n}')
    url = factory.Faker('url')

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.name)
