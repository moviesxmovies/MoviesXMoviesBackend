from django.urls import reverse
from rest_framework import serializers

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
