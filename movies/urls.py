from django.urls import path

from . import views

app_name = 'movies'

urlpatterns = [
    path('<movie:movie>/', views.movie_detail, name='movie-detail'),
    path('<movie:movie>/reviews/', views.movie_review_wrapper, name='movie-reviews-wrapper'),
    path('<movie:movie>/ratings/', views.movie_rating_wrapper, name='movie-ratings-wrapper'),
    path(
        '<movie:movie>/friends-ratings/',
        views.movie_friends_ratings,
        name='movie-friends-ratings',
    ),
]
