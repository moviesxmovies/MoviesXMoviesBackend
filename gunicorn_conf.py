def post_fork(server, worker):
    import os

    os.environ['GUNICORN_WORKER'] = 'true'


def when_ready(server):
    """Called just after the master process is initialized."""
    import os

    import django

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
    os.environ['SCHEDULE_RQ_JOB'] = 'true'
    django.setup()

    from datetime import datetime, time, timedelta

    import django_rq
    from django.utils import timezone

    from movies.tasks import retrain_professional_model

    scheduler = django_rq.get_scheduler('default')

    for job in scheduler.get_jobs():
        if job.func_name == 'movies.tasks.retrain_professional_model':
            try:
                scheduler.cancel(job)
            except Exception:
                pass

    now = timezone.now()
    scheduled_time = datetime.combine(now.date(), time(3, 0))
    scheduled_time = timezone.make_aware(scheduled_time)
    if scheduled_time < now:
        scheduled_time += timedelta(days=1)

    scheduler.schedule(
        scheduled_time=scheduled_time,
        func=retrain_professional_model,
        interval=86400,
        repeat=None,
    )
    server.log.info(f'Job scheduled from gunicorn master: {scheduled_time}')
