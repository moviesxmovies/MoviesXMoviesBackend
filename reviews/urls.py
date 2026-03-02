from django.urls import path

from reviews.views import review_wrapper

app_name = 'reviews'

urlpatterns = [
    path('<review:review>/', review_wrapper, name='movie-reviews'),
]
