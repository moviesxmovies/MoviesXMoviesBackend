import json
import os
import time

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

LOG_FILES = {
    'all': os.path.join(settings.LOG_BASE_DIR, 'django_all.log'),
    'error': os.path.join(settings.LOG_BASE_DIR, 'django_error.log'),
}

DEFAULT_TAIL_LINES = 200


def _tail_file(filepath, n=DEFAULT_TAIL_LINES):
    """Efficiently reads the last n lines of a file."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return list(f)[-n:]
    except OSError:
        return []


@staff_member_required
def admin_log_viewer(request):
    """Renders the log viewer admin page."""
    log_type = request.GET.get('log', 'all')
    if log_type not in LOG_FILES:
        log_type = 'all'

    filepath = LOG_FILES[log_type]
    lines = _tail_file(filepath)

    context = {
        'title': 'Log Viewer',
        'log_type': log_type,
        'log_files': list(LOG_FILES.keys()),
        'initial_lines': ''.join(lines),
        'has_permission': True,
    }
    return render(request, 'admin/log_viewer.html', context)


@staff_member_required
@require_GET
def admin_log_stream(request):
    """
    SSE endpoint that streams new log lines as they are appended.
    The client sends ?log=all|error&offset=<byte_offset>.
    """
    log_type = request.GET.get('log', 'all')
    if log_type not in LOG_FILES:
        log_type = 'all'

    filepath = LOG_FILES[log_type]

    # Start from the end of the file
    try:
        initial_offset = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    except OSError:
        initial_offset = 0

    def event_stream():
        offset = initial_offset
        # Send a heartbeat comment immediately so the browser knows the connection is alive
        yield ': connected\n\n'
        while True:
            try:
                if not os.path.exists(filepath):
                    time.sleep(1)
                    yield ': waiting\n\n'
                    continue

                current_size = os.path.getsize(filepath)
                if current_size < offset:
                    # File was rotated — reset to beginning
                    offset = 0

                if current_size > offset:
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(offset)
                        new_data = f.read(current_size - offset)
                    offset = current_size
                    for line in new_data.splitlines():
                        line = line.strip()
                        if line:
                            payload = json.dumps({'line': line})
                            yield f'data: {payload}\n\n'
                else:
                    # Heartbeat every 5 s to keep the connection open
                    yield ': heartbeat\n\n'

            except OSError:
                yield ': error\n\n'

            time.sleep(1)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
