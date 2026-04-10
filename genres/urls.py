from django.urls import path
from . import views

app_name = 'genres'

urlpatterns = [
    path('', views.genre_list, name='genre-list'),
]
