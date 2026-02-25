from shared.utils import get_object_or_json_404

from .models import User


class UserConverter:
    regex = r'[\w]+'

    def to_python(self, username: str) -> User:
        return get_object_or_json_404(User, username=username)

    def to_url(self, user: User) -> str:

        return user.username
