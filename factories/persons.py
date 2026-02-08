import factory
from django.utils.text import slugify

from persons.models import Person


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    name = factory.Faker('name')

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.name)

    image = factory.django.ImageField(color='gray', width=200, height=200)

    country = factory.Iterator(Person.Country.values)
