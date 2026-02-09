from shared.serializers import BaseSerializer


class ReviewSerializer(BaseSerializer):
    def serialize_instance(self, review) -> dict:
        return {
            'id': review.id,
            'title': review.title,
            'movie': review.movie.slug,
            'user': review.user.username,
            'content': review.content,
            'is_positive': review.is_positive,
            'created_at': review.created_at.isoformat(),
        }
