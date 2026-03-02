from django.urls import reverse
from rest_framework import serializers

from shared.serializers import BaseSerializer


class MovieListSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
            'privacity': instance.privacity,
            'user': self.build_url(reverse('user-detail', args=[instance.user])),
            'movies': [
                self.build_url(reverse('movies:movie-detail', args=[movie]))
                for movie in instance.movies.all()
            ],
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat(),
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
            'privacity': serializers.CharField(),
            'user': serializers.URLField(),
            'movies': serializers.ListField(child=serializers.URLField()),
            'created_at': serializers.DateTimeField(),
            'updated_at': serializers.DateTimeField(),
        }
