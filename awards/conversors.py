from awards.models import Award
from shared.utils import get_object_or_json_404


class AwardConverter:
    regex = r'[^/]+'

    def to_python(self, slug: str) -> Award:
        return get_object_or_json_404(Award, slug=slug)

    def to_url(self, award: Award) -> str:
        return award.slug
