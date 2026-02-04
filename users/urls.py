from django.urls import path, include
from shared.views import GoogleLogin
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path(
        'auth/login/',
        TokenObtainPairView.as_view(),
        name='token_obtain_pair',
    ),
    path(
        'auth/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh',
    ),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/google/', GoogleLogin.as_view(), name='google_rest_login'),
]
