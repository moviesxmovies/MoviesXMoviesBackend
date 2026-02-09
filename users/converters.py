from http import HTTPStatus

from django.http import JsonResponse

from .models import User


class UserConverter:
    regex = r'[\w]+'

    def to_python(self, username: int) -> User:
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=HTTPStatus.NOT_FOUND)

    def to_url(self, user: User) -> int:

        return user.username
