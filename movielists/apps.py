from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MovielistsConfig(AppConfig):
    name = 'movielists'
    verbose_name = _('Movie Lists')
