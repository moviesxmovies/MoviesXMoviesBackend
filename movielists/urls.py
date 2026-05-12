from django.urls import path

from . import views

app_name = 'movie_lists'


urlpatterns = [
    path('', views.movies_list_self_wrapper, name='movies-lists-self-wrapper'),
    path('searching/', views.movies_list_search, name='movies-lists-search'),
    path(
        '<user:user>/<str:movies_list_slug>/',
        views.movies_list_wrapper,
        name='movies-lists-wrapper',
    ),
    path(
        '<user:user>/<str:movies_list_slug>/movies/searching/',
        views.movies_list_movie_search,
        name='movies-lists-movies-search',
    ),
    path('<user:user>/', views.movies_list_list, name='movies-lists-user'),
    path(
        '<user:user>/<str:movies_list_slug>/<movie:movie>/',
        views.movies_list_movie_wrapper,
        name='movies-lists-movie-wrapper',
    ),
]
