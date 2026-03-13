from django.utils import translation

import logging
import time

logger = logging.getLogger('requests')

class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            f'{request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "-"))} '
            f'"{request.method} {request.get_full_path()}" '
            f'{response.status_code} '
            f'{duration_ms:.1f}ms'
        )
        return response

class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        previous_language = translation.get_language()

        try:
            response = self.get_response(request)
        finally:
            if previous_language:
                translation.activate(previous_language)
            else:
                translation.deactivate()

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        if user and hasattr(user, 'preferred_language') and user.preferred_language:
            translation.activate(user.preferred_language)
            request.LANGUAGE_CODE = user.preferred_language
