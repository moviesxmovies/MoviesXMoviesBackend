
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, register_converter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from movielists.converters import MovieListConverter
from users.converters import UserConverter
# CONVERTERS
register_converter(UserConverter, 'user')
register_converter(MovieListConverter, 'movies-list')

# HANDLERS
handler404 = 'shared.handlers.custom_handler404'
# URLS



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/movies-lists/', include('movielists.urls')),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/', include('users.urls')),
    path('django-rq/', include('django_rq.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
