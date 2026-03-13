from django.db.models import Count, QuerySet
from django.urls import reverse
from rest_framework import serializers

from reviews.models import Reaction
from shared.serializers import BaseSerializer


class ReviewSerializer(BaseSerializer):
    def serialize_instance(self, review) -> dict:
        return {
            'id': review.id,
            'title': review.title,
            'movie': self.build_url(reverse('movies:movie-detail', args=[review.movie])),
            'user': self.build_url(reverse('user-detail', args=[review.user])),
            'content': review.content,
            'is_positive': review.is_positive,
            'created_at': review.created_at.isoformat(),
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'title': serializers.CharField(),
            'movie': serializers.URLField(),
            'user': serializers.URLField(),
            'content': serializers.CharField(),
            'is_positive': serializers.BooleanField(),
            'created_at': serializers.DateTimeField(),
        }


class ReactionManySerializer(BaseSerializer):
    def serialize(self) -> dict:
        reactions_queryset: QuerySet = self.to_serialize
        user = self.request.user
        emoji_display = dict(Reaction.EmojiType.choices)

        counts_query = reactions_queryset.values('emoji').annotate(total=Count('emoji'))
        counts = {emoji_display[r['emoji']]: r['total'] for r in counts_query}

        your_reactions = {}
        if user and user.is_authenticated:
            user_reacs = reactions_queryset.filter(user=user).values('emoji', 'id')
            your_reactions = {emoji_display[r['emoji']]: r['id'] for r in user_reacs}

        return {'reactions': counts, 'your_reactions': your_reactions}

    @staticmethod
    def get_fields_dict():
        return {
            'reactions': serializers.DictField(child=serializers.IntegerField()),
            'your_reactions': serializers.DictField(child=serializers.IntegerField()),
        }


class ReactionSerializer(BaseSerializer):
    def serialize_instance(self, reaction) -> dict:
        return {
            'user': self.build_url(reverse('user-detail', args=[reaction.user.pk])),
            'emoji': reaction.get_emoji_display(),
            'emoji_code': reaction.emoji,
            'target': self.build_url(reaction.target.get_absolute_url()),
        }

    @staticmethod
    def get_fields_dict():
        return {
            'user': serializers.URLField(),
            'emoji': serializers.CharField(help_text='Visual emoji'),
            'emoji_code': serializers.CharField(help_text='Code'),
            'target': serializers.URLField(),
        }


class CommentSerializer(BaseSerializer):
    def serialize_instance(self, comment) -> dict:
        return {
            'id': comment.id,
            'user': self.build_url(reverse('user-detail', args=[comment.user])),
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'reply_comment': self.build_url(
                reverse(
                    'reviews:comment-wrapper-with-id', args=[comment.review, comment.reply_comment]
                )
            )
            if comment.reply_comment
            else None,
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'user': serializers.URLField(),
            'content': serializers.CharField(),
            'created_at': serializers.DateTimeField(),
            'reply_comment': serializers.URLField(),
        }
