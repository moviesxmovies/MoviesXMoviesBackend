def post_fork(server, worker):
    import os

    os.environ['GUNICORN_WORKER'] = 'true'
