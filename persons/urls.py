from django.urls import path
from persons import views

app_name = 'persons'

urlpatterns = [
    path('<person:person>/', views.person_detail, name='person-detail'),
]