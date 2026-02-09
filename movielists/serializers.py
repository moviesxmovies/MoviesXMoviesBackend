from movies.serializers import MovieSerializer
from shared.serializers import BaseSerializer
from users.serializers import UserSerializer

# TODO: CHANGE ALL SERIALIZERS, TO USE A REVERSE TO THE DETAIL URL, EXAMPLE: 'movie': self.build_url(reverse('movies:detail', kwargs={'slug': instance.movie.slug}))
class MovieListSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
            'privacity': instance.privacity,
            'user': UserSerializer(instance.user, request=self.request).serialize(),
            'movies': MovieSerializer(instance.movies.all(), request=self.request).serialize(),
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat(),
        }
