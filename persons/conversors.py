from persons.models import Person
from shared.utils import get_object_or_json_404


class PersonConverter:
    regex = r'[^/]+'

    def to_python(self, slug: str) -> Person:
        return get_object_or_json_404(Person, slug=slug)

    def to_url(self, person: Person) -> str:
        return person.slug
