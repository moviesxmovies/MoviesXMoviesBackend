from shared.serializers import BaseSerializer


class RatingSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'movie': instance.movie.slug,
            'user': instance.user.username,
            'rating': instance.rating,
            'created_at': instance.created_at.isoformat(),
        }
