from django.urls import reverse
from rest_framework import serializers
from django.db.models import Count

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


# TODO: Refactor this


class ReactionsSerializer(BaseSerializer):
    def serialize_instance(self, reactions_queryset) -> dict:
        user = self.request.user

        counts_query = reactions_queryset.values('emoji').annotate(total=Count('emoji'))
        counts = {r['emoji']: r['total'] for r in counts_query}

        your_reactions = {}
        if user and user.is_authenticated:
            user_reacs = reactions_queryset.filter(user=user).values('emoji', 'id')
            your_reactions = {r['emoji']: r['id'] for r in user_reacs}

        return {'reactions': counts, 'your_reactions': your_reactions}
