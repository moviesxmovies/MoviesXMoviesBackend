from django.urls import path

from . import views


app_name = 'movies'

urlpatterns = [
    path('<movie:movie>/', views.movie_detail, name='movie-detail'),
]
