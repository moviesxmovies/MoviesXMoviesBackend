from django.http import JsonResponse


def custom_handler404(request,exception):
    data = getattr(
        exception,
        'custom_data',
        {
            'error': 'Not Found',
            'message': 'The requested resource was not found.',
            'model': getattr(exception, 'model_name', 'unknown'),
            'lookup_value': getattr(exception, 'lookup_value', 'unknown'),
        },
    )
    return JsonResponse(data, status=404)
