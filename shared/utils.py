import logging

import deepl
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import _get_queryset
from django.utils import translation
from django.utils.translation import gettext as _

from main import settings

logger = logging.getLogger(__name__)


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


def __get_cursor_filter(queryset, last_id, ordering_field):
    if not last_id:
        return queryset

    fields = ordering_field if isinstance(ordering_field, list) else [ordering_field]
    non_pk_fields = [f for f in fields if f.lstrip('-') != 'pk']

    if not non_pk_fields:
        return queryset.filter(pk__lt=last_id)

    try:
        last_item = queryset.get(pk=last_id)
    except queryset.model.DoesNotExist:
        return queryset

    filter_q = Q()
    equal_conditions = Q()

    for field_expr in non_pk_fields:
        descending = field_expr.startswith('-')
        field_name = field_expr.lstrip('-')
        field_value = getattr(last_item, field_name)
        lookup = f'{field_name}__{"lt" if descending else "gt"}'

        filter_q |= equal_conditions & Q(**{lookup: field_value})
        equal_conditions &= Q(**{field_name: field_value})

    filter_q |= equal_conditions & Q(pk__lt=last_id)

    return queryset.filter(filter_q).distinct()


def __apply_ordering(queryset, ordering_field):
    if isinstance(ordering_field, list):
        return queryset.order_by(*ordering_field, '-pk')
    return queryset.order_by(ordering_field, '-pk')


def get_progressive_response(
    queryset, serializer_class, request, last_id=None, limit=10, ordering_field='-pk', order=True
):
    limit = int(limit) if limit else 10
    last_id = int(last_id) if last_id else None
    count = queryset.count()
    queryset = __get_cursor_filter(queryset, last_id, ordering_field)

    if order:
        queryset = __apply_ordering(queryset, ordering_field)
    items = list(queryset[: limit + 1])

    has_more = len(items) > limit
    if has_more:
        items = items[:-1]

    return JsonResponse(
        {
            'results': serializer_class(items, request=request).serialize(),
            'next_last_id': items[-1].pk if has_more and items else None,
            'count': count,
        }
    )


translator = deepl.Translator(settings.DEEPL_API_KEY)


def translate_text(text: str, target_lang: str = 'en') -> str:
    lang_map = {
        'en': 'EN-US',
        'es': 'ES',
        'fr': 'FR',
        'de': 'DE',
    }
    try:
        result = translator.translate_text(text, target_lang=lang_map[target_lang])
    except deepl.AuthorizationException as e:
        logger.error(f'DeepL authorization error: {e}')
        return text
    except deepl.DeepLException as e:
        logger.error(f'DeepL error: {e}')
        return text
    except KeyError:
        logger.warning(f'Unsupported target language for translation: {target_lang}')
        return text
    except deepl.ConnectionException as e:
        logger.error(f'DeepL connection error: {e}')
        return text
    except deepl.QuotaExceededException as e:
        logger.error(f'DeepL quota exceeded: {e}')
        return text
    except deepl.TooManyRequestsException as e:
        logger.error(f'DeepL too many requests: {e}')
        return text

    if isinstance(result, list):
        return result[0].text
    return result.text
