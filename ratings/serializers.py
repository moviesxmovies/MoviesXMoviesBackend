from django.urls import reverse

from shared.serializers import BaseSerializer


class RatingSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'movie': self.build_url(reverse('movies:movie-detail', kwargs={'slug': instance.movie.slug})),
            'user': self.build_url(reverse('user-detail', kwargs={'slug': instance.user.slug})),
            'rating': instance.rating,
            'created_at': instance.created_at.isoformat(),
        }
