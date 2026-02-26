from django.urls import path

from . import views

app_name = 'movie_lists'


urlpatterns = [
    path('', views.movies_list_self, name='movies-lists-self'),
    path('<user:user>/', views.movies_list_list, name='movies-lists-user'),
    path(
        '<user:user>/<movies-list:movies_list>/', views.movies_list_detail, name='movies-lists-user'
    ),
]
