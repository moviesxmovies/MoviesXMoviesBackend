from io import BytesIO

import requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.files import File

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
        picture_url = data.get('picture')
        if picture_url and not user.picture:
            try:
                response = requests.get(picture_url, timeout=5)
                if response.status_code == 200:
                    filename = f'profile_{user.pk}.jpg'
                    user.picture.save(filename, File(BytesIO(response.content)), save=True)
            except requests.RequestException:
                pass
        return user
