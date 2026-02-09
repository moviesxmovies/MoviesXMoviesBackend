from shared.serializers import BaseSerializer


# TODO: CHANGE ALL SERIALIZERS, TO USE A REVERSE TO THE DETAIL URL, EXAMPLE: 'movie': self.build_url(reverse('movies:detail', kwargs={'slug': instance.movie.slug}))
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
