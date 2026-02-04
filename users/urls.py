from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from shared.views import CustomTokenObtainPairView

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
]
