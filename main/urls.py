from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, register_converter
from django.urls.converters import get_converters
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from movielists.converters import MovieListConverter
from movies.converters import MovieConverter
from reviews.converters import CommentConverter, ReactionConverter, ReviewConverter
from users.converters import UserConverter

# CONVERTERS
CUSTOM_CONVERTERS = {
    'user': UserConverter,
    'movies-list': MovieListConverter,
    'movie': MovieConverter,
    'review': ReviewConverter,
    'comment': CommentConverter,
    'reaction': ReactionConverter,
}

registered = get_converters()
for name, converter_class in CUSTOM_CONVERTERS.items():
    if name not in registered:
        register_converter(converter_class, name)

# HANDLERS
handler404 = 'shared.handlers.custom_handler404'

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/movies-lists/', include('movielists.urls')),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/', include('users.urls')),
    path('api/movies/', include('movies.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('django-rq/', include('django_rq.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
