from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from shared.utils import activate_request_language, deactivate_language
from users.models import User

from .serializers import CustomTokenObtainPairSerializer


class GoogleLogin(SocialLoginView):
    """
    View for handling Google social login using the allauth library. This view uses the GoogleOAuth2Adapter to manage the OAuth2 flow and the OAuth2Client to handle the client-side interactions.
    The callback URL is dynamically generated based on the request's security and host information, allowing for flexibility in different deployment environments.
    """

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        protocol = 'https' if self.request.is_secure() else 'http'
        host = self.request.get_host() if self.request.is_secure() else 'localhost:5173'

        return f'{protocol}://{host}/accounts/google/login/callback/'


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View for obtaining JWT token pairs (access and refresh tokens) using a custom serializer. This view extends the default TokenObtainPairView provided by the Simple JWT library, allowing for customization of the token generation process through the CustomTokenObtainPairSerializer.
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        previous_language = activate_request_language(request)
        try:
            return super().post(request, *args, **kwargs)
        finally:
            deactivate_language(previous_language)


class CustomTokenRefreshView(TokenRefreshView):
    """
    View for refreshing JWT access tokens using a refresh token.
    """

    def post(self, request, *args, **kwargs):
        previous_language = activate_request_language(request)
        try:
            response = super().post(request, *args, **kwargs)

            if response.status_code == 200:
                refresh = RefreshToken(request.data['refresh'])
                user_id = refresh['user_id']
                user = User.objects.get(id=user_id)

                new_refresh = RefreshToken.for_user(user)
                new_refresh['username'] = user.username
                new_refresh['boarded'] = user.boarded
                new_refresh['verified'] = user.verified

                response.data['access'] = str(new_refresh.access_token)

            return response
        finally:
            deactivate_language(previous_language)
