from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from shared.views import CustomTokenObtainPairView, GoogleLogin
from users import views

urlpatterns = [
    path(
        'auth/login/',
        CustomTokenObtainPairView.as_view(),
        name='token_obtain_pair',
    ),
    path(
        'auth/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh',
    ),
    path('auth/verify/', views.verify_user, name='verify_user'),
    path('oauth/', include('dj_rest_auth.urls')),
    path('oauth/google/', GoogleLogin.as_view(), name='google_rest_login'),
]
