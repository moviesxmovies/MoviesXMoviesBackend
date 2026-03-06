import json
from http import HTTPStatus
from django.http import JsonResponse
from django.utils.translation import gettext as _


def require_http_methods(methods):
    """Decorator factory that restricts a view to specific HTTP methods.

    Args:
        methods (list[str]): A list of allowed HTTP method strings
            (e.g., ``['GET', 'POST']``).

    Returns:
        Callable: A decorator that wraps a view function and enforces
        the allowed HTTP methods.

    Example:
        @require_http_methods(['GET', 'POST'])
        def my_view(request):
            ...
    """

    def decorator(func):
        """Wraps the view function with HTTP method enforcement.

        Args:
            func (Callable): The view function to wrap.

        Returns:
            Callable: The wrapped view function.
        """

        def wrapper(request, *args, **kwargs):
            """Checks the request method and delegates or rejects.

            Args:
                request (HttpRequest): The incoming Django HTTP request.
                *args: Positional arguments forwarded to the view.
                **kwargs: Keyword arguments forwarded to the view.

            Returns:
                JsonResponse: A 405 Method Not Allowed response if the
                request method is not in ``methods``, otherwise the
                result of calling the wrapped view function.
            """
            if request.method not in methods:
                return JsonResponse(
                    {'error': _('Method not allowed')},
                    status=HTTPStatus.METHOD_NOT_ALLOWED,
                )
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_query_params(*params_names):
    """Decorator factory that extracts named query parameters from the request.

    Reads each named parameter from ``request.GET`` and injects them as
    keyword arguments into the wrapped view. Missing parameters are passed
    as ``None``.

    Args:
        *params_names (str): Variable number of query parameter names to
            extract from the URL query string.

    Returns:
        Callable: A decorator that wraps a view function and injects the
        extracted query parameters as keyword arguments.

    Example:
        @get_query_params('page', 'limit')
        def my_view(request, page=None, limit=None):
            ...
    """

    def decorator(func):
        """Wraps the view function with query parameter extraction.

        Args:
            func (Callable): The view function to wrap.

        Returns:
            Callable: The wrapped view function.
        """

        def wrapper(request, *args, **kwargs):
            """Extracts query params and forwards them to the view.

            Args:
                request (HttpRequest): The incoming Django HTTP request.
                *args: Positional arguments forwarded to the view.
                **kwargs: Keyword arguments forwarded to the view.
                    Extracted query parameters are merged into this dict.

            Returns:
                Any: The result of calling the wrapped view function.
            """
            extracted_params = {}
            for param_name in params_names:
                extracted_params[param_name] = request.GET.get(param_name)
            kwargs.update(extracted_params)
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_body(model_class, required_fields):
    """Decorator factory that parses and validates the JSON request body.

    Deserializes the request body as JSON, validates that all
    ``required_fields`` are present, and either instantiates a
    ``model_class`` object or passes the raw dict to the view.

    Args:
        model_class (type | None): A class to instantiate with the
            extracted fields as keyword arguments. If ``None``, the
            cleaned data dict is passed directly under the ``body``
            keyword argument.
        required_fields (list[str]): A list of field names that must be
            present in the JSON body. Returns 400 if any are missing.

    Returns:
        Callable: A decorator that wraps a view function and injects the
        parsed body (or model instance) as a keyword argument.

    Raises:
        JsonResponse (400): If the request body is not valid JSON.
        JsonResponse (400): If any field in ``required_fields`` is absent
            from the parsed body.

    Example:
        @get_body(UserModel, ['username', 'email'])
        def my_view(request, usermodel=None):
            ...

        @get_body(None, ['username', 'email'])
        def my_view(request, body=None):
            ...
    """

    def decorator(func):
        """Wraps the view function with JSON body parsing and validation.

        Args:
            func (Callable): The view function to wrap.

        Returns:
            Callable: The wrapped view function.
        """

        def wrapper(request, *args, **kwargs):
            """Parses the request body and injects it into the view.

            Args:
                request (HttpRequest): The incoming Django HTTP request.
                    ``request.body`` must contain a valid JSON payload.
                *args: Positional arguments forwarded to the view.
                **kwargs: Keyword arguments forwarded to the view.
                    The parsed model instance is added under the
                    lowercased class name, or under ``body`` if
                    ``model_class`` is ``None``.

            Returns:
                Any: The result of calling the wrapped view function,
                or a ``JsonResponse`` with a 400 status on failure.
            """
            try:
                body_data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse(
                    {'error': _('Invalid JSON body')},
                    status=HTTPStatus.BAD_REQUEST,
                )

            clean_data = {}
            for field in required_fields:
                if field not in body_data:
                    return JsonResponse(
                        {'error': _('Missing required fields')},
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
