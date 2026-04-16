from django.http import JsonResponse
from django.utils.translation import gettext as _

def custom_handler404(request, exception):
    data = getattr(
        exception,
        'custom_data',
        {
            'error': _('Not Found'),
            'message': _('The requested resource was not found.'),
            'model': getattr(exception, 'model_name', _('unknown')),
            'lookup_value': getattr(exception, 'lookup_value', _('unknown')),
        },
    )
    return JsonResponse(data, status=404)
