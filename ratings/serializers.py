from shared.serializers import BaseSerializer

# TODO: CHANGE ALL SERIALIZERS, TO USE A REVERSE TO THE DETAIL URL, EXAMPLE: 'movie': self.build_url(reverse('movies:detail', kwargs={'slug': instance.movie.slug}))
class RatingSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'movie': instance.movie.slug,
            'user': instance.user.username,
            'rating': instance.rating,
            'created_at': instance.created_at.isoformat(),
        }
