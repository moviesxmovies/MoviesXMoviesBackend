from django.urls import path

from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.get_movie_recommendations, name='movies-recommendations'),
    path('searching/', views.movie_search, name='movie-search'),
    path('<movie:movie>/', views.movie_detail, name='movie-detail'),
    path('<movie:movie>/reviews/', views.movie_review_wrapper, name='movie-reviews-wrapper'),
    path('<movie:movie>/ratings/', views.movie_rating_wrapper, name='movie-ratings-wrapper'),
    path('<movie:movie>/unseen/', views.movie_unseen_wrapper, name='movie-unseen-wrapper'),
    path(
        '<movie:movie>/friends-ratings/',
        views.movie_friends_ratings,
        name='movie-friends-ratings',
    ),
    path('<movie:movie>/movie-lists/', views.self_movie_lists_slug, name='movie-movie-lists'),
]
