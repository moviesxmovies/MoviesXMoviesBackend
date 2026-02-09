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
