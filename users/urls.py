from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from ratelimit.decorators import ratelimit

urlpatterns = [
    path(
        'auth/login/',
        ratelimit(key='ip', rate='5/m', method='POST', block=True)(TokenObtainPairView.as_view()),
        name='token_obtain_pair',
    ),
    path(
        'auth/refresh/',
        ratelimit(key='ip', rate='10/m', method='POST', block=True)(TokenRefreshView.as_view()),
        name='token_refresh',
    ),
]
