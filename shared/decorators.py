import json
from http import HTTPStatus

from django.http import JsonResponse


def require_http_methods(methods):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return JsonResponse(
                    {'error': 'Method not allowed'},
                    status=HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_query_params(*params_names):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            extracted_params = {}
            for param_name in params_names:
                extracted_params[param_name] = request.GET.get(param_name)

            kwargs.update(extracted_params)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_body(model_class, required_fields):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            try:
                body_data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON body'}, status=HTTPStatus.BAD_REQUEST)

            clean_data = {}
        
            for field in required_fields:
                if field not in body_data:
                    return JsonResponse(
                        {'error': 'Missing required fields'},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                clean_data[field] = body_data[field]
            if model_class:
                instance = model_class(**clean_data)
                kwargs[model_class.__name__.lower()] = instance

            else:
                instance = clean_data
                kwargs['body'] = instance
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
