from django.urls import reverse

from shared.serializers import BaseSerializer
from rest_framework import serializers


class RatingSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'user': self.build_url(reverse('user-detail', args=[instance.user])),
            'movie': self.build_url(reverse('movies:movie-detail', args=[instance.movie])),
            'rating': instance.rating,
            'created_at': instance.created_at.isoformat(),
        }
    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'user': serializers.URLField(),
            'movie': serializers.URLField(),
            'rating': serializers.IntegerField(),
            'created_at': serializers.DateTimeField(),
        }
