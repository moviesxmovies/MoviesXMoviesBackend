from rest_framework import serializers

from awards.serializers import AwardSerializer
from genres.serializers import GenreSerializer
from persons.serializers import PersonSerializer
from platforms.serializers import PlatformSerializer
from shared.serializers import BaseSerializer


class MovieSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'title': instance.title,
            'slug': instance.slug,
            'release_date': instance.release_date.isoformat(),
            'synopsis': instance.synopsis,
            'cover': self.build_url(instance.cover.url),
            'genres': GenreSerializer(instance.genres.all(), request=self.request).serialize(),
            'awards': AwardSerializer(instance.awards.all(), request=self.request).serialize(),
            'platforms': PlatformSerializer(
                instance.platforms.all(), request=self.request
            ).serialize(),
            'actors': PersonSerializer(instance.actors.all(), request=self.request).serialize(),
            'directors': PersonSerializer(
                instance.directors.all(), request=self.request
            ).serialize(),
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'title': serializers.CharField(),
            'slug': serializers.CharField(),
            'release_date': serializers.DateField(),
            'synopsis': serializers.CharField(),
            'cover': serializers.URLField(),
            'genres': GenreSerializer.get_fields_schema(),
            'awards': AwardSerializer.get_fields_schema(),
            'platforms': PlatformSerializer.get_fields_schema(),
            'actors': PersonSerializer.get_fields_schema(),
            'directors': PersonSerializer.get_fields_schema(),
        }
