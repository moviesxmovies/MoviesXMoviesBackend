from django.urls import reverse

from shared.serializers import BaseSerializer


class ReviewSerializer(BaseSerializer):
    def serialize_instance(self, review) -> dict:
        return {
            'id': review.id,
            'title': review.title,
            'movie': self.build_url(reverse('movies:movie-detail', args=[review.movie])),
            'user': self.build_url(reverse('user-detail', args=[review.user])),
            'content': review.content,
            'is_positive': review.is_positive,
            'created_at': review.created_at.isoformat(),
        }
