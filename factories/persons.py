import factory
from django.utils.text import slugify

from main import settings
from persons.models import Person

from .awards import AwardFactory


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    name = factory.Faker('name')

    @factory.lazy_attribute_sequence
    def slug(self, n):
        return f'{slugify(self.name)}-{n}'

    image = factory.django.ImageField(color='gray', width=200, height=200)
    biography = factory.Faker('paragraph', nb_sentences=5)
    birthday = factory.Faker('date_of_birth')
    deathday = factory.Faker('date_of_birth')
    gender = factory.Faker(
        'random_element', elements=[choice[0] for choice in Person.Gender.choices]
    )

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
            translation.person = self
            translation.save()


class PersonTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person.PersonTranslation
        exclude = ['_save']

    language = factory.Iterator(settings.SUPPORTED_LANGUAGES)
    biography = factory.Faker('paragraph', nb_sentences=5)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class(*args, **kwargs)
