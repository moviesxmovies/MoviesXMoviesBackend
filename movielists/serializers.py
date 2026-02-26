from movies.serializers import MovieSerializer
from shared.serializers import BaseSerializer
from django.urls import reverse


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
