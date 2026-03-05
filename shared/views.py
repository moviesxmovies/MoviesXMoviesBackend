from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.views import TokenObtainPairView

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
