from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AwardsConfig(AppConfig):
    name = 'awards'
    verbose_name = _('Awards')
