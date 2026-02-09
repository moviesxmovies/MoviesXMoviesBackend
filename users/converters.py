from django.shortcuts import get_object_or_404

from .models import User


class UserConverter:
    regex = r'[\w]+'

    def to_python(self, username: int) -> User:
        return get_object_or_404(User, username=username)

    def to_url(self, user: User) -> int:

        return user.username
