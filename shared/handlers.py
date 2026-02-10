from django.http import JsonResponse


def handler404(request, exception):
    message = 'Not found'
    if not request:
        return JsonResponse({'error': message}, status=404)

    if exception:
        msg = str(exception)
        if 'No ' in msg and ' matches' in msg:
            model_name = msg.split(' ')[1]
            message = f'{model_name} not found'
        else:
            message = msg

    return JsonResponse({'error': message.capitalize()}, status=404)
