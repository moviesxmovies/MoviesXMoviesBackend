import factory
from django.utils.text import slugify

from awards.models import Award


class AwardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Award
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Award {n}')

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.name)

    category = factory.Iterator(Award.Category.values)

    date = factory.Faker('date_this_decade')

    icon = factory.django.ImageField(color='gold', width=100, height=100)
