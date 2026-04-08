from django.urls import reverse
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
            'title': instance.translate_title(self.request.user.preferred_language)
            if self.request
            else instance.title,
            'slug': instance.slug,
            'release_date': instance.release_date.isoformat(),
            'synopsis': instance.translate_synopsis(self.request.user.preferred_language)
            if self.request
            else instance.synopsis,
            'cover': self.build_url(
                instance.translate_image(self.request.user.preferred_language)
                if self.request
                else instance.cover.url
            ),
            'genres': GenreSerializer(instance.genres.all(), request=self.request).serialize(),
            'awards': [
                self.build_url(reverse('awards:award-detail', args=[award]))
                for award in instance.awards.all()
            ],
            'platforms': PlatformSerializer(
                instance.platforms.all(), request=self.request
            ).serialize(),
            'actors': [
                self.build_url(reverse('persons:person-detail', args=[actor]))
                for actor in instance.actors.all()
            ],
            'directors': [
                self.build_url(reverse('persons:person-detail', args=[director]))
                for director in instance.directors.all()
            ],
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
            'awards': serializers.ListField(child=serializers.URLField()),
            'platforms': PlatformSerializer.get_fields_schema(),
            'actors': serializers.ListField(child=serializers.URLField()),
            'directors': serializers.ListField(child=serializers.URLField()),
        }
