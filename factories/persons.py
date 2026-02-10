import factory
from django.utils.text import slugify

from persons.models import Person

from .awards import AwardFactory


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    name = factory.Faker('name')

    @factory.lazy_attribute
    def slug(self):
        return slugify(self.name)

    image = factory.django.ImageField(color='gray', width=200, height=200)


    @factory.post_generation
    def awards(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.awards.add(*extracted)
        else:
            self.awards.add(AwardFactory())
