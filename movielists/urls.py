from django.urls import path, register_converter

from users.converters import UserConverter

from . import views
from .converters import MovieListConverter

app_name = 'movie_lists'

register_converter(MovieListConverter, 'movies-list')
register_converter(UserConverter, 'user')


urlpatterns = [
    path('', views.movies_list_self, name='movies-lists-self'),
    path('<user:user>/', views.movies_list_list, name='movies-lists-user'),
    path(
        '<user:user>/<movies-list:movies_list>/', views.movies_list_detail, name='movies-lists-user'
    ),
]
