from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PlatformsConfig(AppConfig):
    name = 'platforms'
    verbose_name = _('Platforms')
