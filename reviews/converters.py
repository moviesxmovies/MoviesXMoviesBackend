from shared.utils import get_object_or_json_404

from .models import Review


class ReviewConverter:
    regex = r'[\d]+'

    def to_python(self, pk: str) -> Review:
        return get_object_or_json_404(Review, pk=pk)

    def to_url(self, review: Review) -> int:
        return review.pk
