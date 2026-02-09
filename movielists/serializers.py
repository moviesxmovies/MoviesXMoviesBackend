from movies.serializers import MovieSerializer
from shared.serializers import BaseSerializer
from users.serializers import UserSerializer


class MovieListSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
            'privacy': instance.privacy,
            'user': UserSerializer(instance.user, request=self.request).serialize(),
            'movies': MovieSerializer(instance.movies.all(), request=self.request).serialize(),
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat(),
        }
