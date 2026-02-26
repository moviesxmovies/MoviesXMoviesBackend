from django.urls import path

from . import views

app_name = 'movies'

urlpatterns = [
    path('<movie:movie>/', views.movie_detail, name='movie-detail'),
    path('movies/<movie:movie>/reviews/', views.movie_reviews, name='movie-reviews'),
    path(
        'movies/<movie:movie>/friends_ratings/',
        views.movie_friends_ratings,
        name='movie-friends-ratings',
    ),
]
