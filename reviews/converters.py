from shared.utils import get_object_or_json_404

from .models import Comment, Reaction, Review

DIGIT_REGEX = r'[\d]+'


class ReviewConverter:
    regex = DIGIT_REGEX

    def to_python(self, pk: str) -> Review:
        return get_object_or_json_404(Review, pk=pk)

    def to_url(self, review: Review) -> int:
        return review.pk


class CommentConverter:
    regex = DIGIT_REGEX

    def to_python(self, pk: str) -> Comment:
        return get_object_or_json_404(Comment, pk=pk)

    def to_url(self, comment: Comment) -> int:
        return comment.pk


class ReactionConverter:
    regex = DIGIT_REGEX

    def to_python(self, pk: str) -> Reaction:
        return get_object_or_json_404(Reaction, pk=pk)

    def to_url(self, reaction: Reaction) -> int:
        return reaction.pk
