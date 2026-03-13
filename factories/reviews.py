import factory
from reviews.models import Review, Comment, Reaction
from .movies import MovieFactory
from .users import UserFactory

class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review
        django_get_or_create = ('user', 'movie')

    title = factory.Faker('sentence', nb_words=6)
    content = factory.Faker('paragraph', nb_sentences=4)
    is_positive = factory.Faker('boolean', chance_of_getting_true=70)
    user = factory.SubFactory(UserFactory)
    movie = factory.SubFactory(MovieFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    content = factory.Faker('paragraph', nb_sentences=2)
    user = factory.SubFactory(UserFactory)
    review = factory.SubFactory(ReviewFactory)
    reply_comment = None


class ReactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reaction
        django_get_or_create = ('user', 'content_type', 'object_id', 'emoji')

    user = factory.SubFactory(UserFactory)
    emoji = Reaction.EmojiType.LIKE