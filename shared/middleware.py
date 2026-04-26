import logging
import time
import uuid

from django.utils import translation
from prometheus_client import Counter

logger = logging.getLogger('requests')

http_responses_total = Counter(
    'http_responses_by_view_total',
    'HTTP responses excluding metrics scraping',
    ['status', 'view', 'method'],
)


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        request.request_id = request_id

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        if not request.path.startswith('/metrics'):
            msg = (
                f'{request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "-"))} '
                f'"{request.method} {request.get_full_path()}" '
                f'{response.status_code} '
                f'[{request.user if hasattr(request, "user") else "-"}] '
                f'{duration_ms:.1f}ms '
                f'[{request_id}]'
            )

            if response.status_code >= 500:
                logger.error(msg)
            elif response.status_code >= 400:
                logger.warning(msg)
            else:
                logger.info(msg)

        if request.resolver_match:
            http_responses_total.labels(
                status=str(response.status_code),
                view=request.resolver_match.view_name,
                method=request.method,
            ).inc()

        response['X-Request-ID'] = request_id
        return response
