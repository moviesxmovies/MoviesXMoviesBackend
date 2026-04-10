from django.urls import path
from persons import views

app_name = 'persons'

urlpatterns = [
    path('actors/', views.actors_pagination, name='actors-pagination'),
    path('directors/', views.directors_pagination, name='directors-pagination'),
    path('<person:person>/', views.person_detail, name='person-detail'),
]
