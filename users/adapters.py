from datetime import datetime
from io import BytesIO

import requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = sociallogin.user.email
        if not email:
            return

        try:
            existing_user = User.objects.get(email=email)
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        data = sociallogin.account.extra_data

        locale = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')[:2]
        user.preferred_language = locale
        user.save(update_fields=['preferred_language'])

        picture_url = data.get('picture')
        if picture_url and self._user_has_default_picture(user):
            self._fetch_and_save_picture(user, picture_url)

        return user

    def _user_has_default_picture(self, user) -> bool:
        try:
            return not user.picture or user.picture.name == 'users/default.png'
        except ValueError:
            return True

    def _fetch_and_save_picture(self, user, picture_url: str) -> None:
        try:
            response = requests.get(picture_url, timeout=5)
            response.raise_for_status()

            filename = (
                f'profile_{user.username}_OAUTH_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
            )
            from django.core.files import File

            user.picture.save(filename, File(BytesIO(response.content)), save=True)

        except requests.RequestException:
            pass
