from django.http import Http404
from django.shortcuts import _get_queryset


def get_object_or_json_404(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        model_name = queryset.model.__name__
        lookup_value = list(kwargs.values())[0] if kwargs else 'unknown'

        msg = f'Does not exist {model_name} with identifier {lookup_value}'
        exc = Http404(msg)
        exc.model_name = model_name
        exc.lookup_value = lookup_value
        raise exc
