from django.urls import include, path

from shared.views import CustomTokenObtainPairView, CustomTokenRefreshView, GoogleLogin
from users import views

urlpatterns = [
    # AUTH
    path(
        'auth/login/',
        CustomTokenObtainPairView.as_view(),
        name='token_obtain_pair',
    ),
    path(
        'auth/refresh/',
        CustomTokenRefreshView.as_view(),
        name='token_refresh',
    ),
    path('auth/signup/', views.user_signup, name='signup'),
    # OAUTH
    path('auth/verify/', views.verify_user, name='verify_user'),
    path(
        'auth/resend-verification-email/',
        views.resend_verification_email,
        name='resend_verification_email',
    ),
    path('auth/forgot-password/', views.forgot_password_wrapper, name='forgot_password'),
    path('oauth/', include('dj_rest_auth.urls')),
    path('oauth/google/', GoogleLogin.as_view(), name='google_rest_login'),
    # USERS
    path('users/onboarding/', views.complete_onboarding, name='complete_onboarding'),
    path('users/suggested-users/', views.suggested_users, name='suggested_users'),
    path(
        'users/preferred-language/',
        views.preferred_language_wrapper,
        name='preferred_language_wrapper',
    ),
    path('users/', views.self_user_wrapper, name='self_user_wrapper'),
    path('users/friend-requests/', views.self_friend_requests, name='self-friend-requests'),
    path('users/friends/', views.self_friend_wrapper, name='self-friends'),
    path('users/searching/', views.user_search, name='user-search'),
    path('users/<user:user>/', views.user_detail, name='user-detail'),
    # REVIEWS
    path('users/<user:user>/reviews/', views.user_reviews, name='user-reviews'),
    # FRIENDS
    path('users/<user:user>/friends/', views.user_friends, name='user-friends'),
    path('users/<user:user>/friend-requests/', views.friend_requests_wrapper, name='friend-requests-wrapper'),
]
