from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import _get_queryset
from django.utils.translation import gettext as _
from django.utils import translation

from main import settings


def get_object_or_json_404(klass, *args, **kwargs):
    """
    Retrieves a single object from the database based on the provided model class and lookup parameters. If the object does not exist, it raises an Http404 exception with a custom error message.

    Args:
        klass (Model or QuerySet): The model class or queryset to query.
        *args: Positional arguments to pass to the queryset's get() method.
        **kwargs: Keyword arguments to pass to the queryset's get() method.

    Returns:
        Model instance: The retrieved object if it exists.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        model_name = queryset.model.__name__
        lookup_value = list(kwargs.values())[0] if kwargs else 'unknown'

        msg = _('Does not exist {model_name} with identifier {lookup_value}').format(
            model_name=model_name, lookup_value=lookup_value
        )
        exc = Http404(msg)
        exc.model_name = model_name
        exc.lookup_value = lookup_value
        raise exc


def get_paginated_response(queryset, serializer_class, request, page, limit):
    """Creates a paginated response

    Args:
        queryset (django.queryset): Queryset to execute and paginate
        serializer_class (): Class to serialize the objects in the queryset
        request (django.request): Request object containing user context
        page (number): Page number to retrieve
        limit (number): Number of items per page

    Returns:
        django.http.JsonResponse: JsonResponse with paginated results and metadata
    """
    page = int(page) if page and str(page).isdigit() else 1
    limit = int(limit) if limit and str(limit).isdigit() else 10

    paginator = Paginator(queryset, limit)
    page_result = paginator.get_page(page)
    serialized_data = [
        serializer_class(obj, request=request).serialize() for obj in page_result.object_list
    ]
    return JsonResponse(
        {
            'results': serialized_data,
            'total_pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': page_result.has_next(),
            'has_previous': page_result.has_previous(),
            'current_page': page_result.number,
        }
    )


def activate_request_language(request):
    previous_language = translation.get_language()
    preferred_language = request.GET.get('lang', settings.DEFAULT_LANGUAGE)
    if preferred_language not in settings.SUPPORTED_LANGUAGES:
        preferred_language = settings.DEFAULT_LANGUAGE
    translation.activate(preferred_language)
    request.LANGUAGE_CODE = preferred_language
    return previous_language


def deactivate_language(previous_language):
    if previous_language:
        translation.activate(previous_language)
    else:
        translation.deactivate()
