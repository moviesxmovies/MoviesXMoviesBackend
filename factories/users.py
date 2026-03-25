import factory

from users.models import FriendRequest, User

from .platforms import PlatformFactory


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    bio = factory.Faker('paragraph', nb_sentences=3)
    boarded = factory.Iterator([True, False])
    verified = factory.Iterator([True, False])
    password = factory.PostGenerationMethodCall('set_password', 'password123')

    @factory.post_generation
    def following_person(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.following_person.add(*extracted)

    @factory.post_generation
    def platforms(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.platforms.add(*extracted)
        else:
            self.platforms.add(PlatformFactory())


class FriendRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FriendRequest

    from_user = factory.SubFactory(UserFactory)
    to_user = factory.SubFactory(UserFactory)
    status = factory.Iterator(FriendRequest.Status.values)
