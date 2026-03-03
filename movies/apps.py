import os
from datetime import datetime, time, timedelta
import sys

from django.apps import AppConfig
from django.utils import timezone


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            if 'test' in sys.argv or 'pytest' in sys.modules:
                return
            try:
                import django_rq

                from .tasks import retrain_professional_model

                scheduler = django_rq.get_scheduler('default')

                for job in scheduler.get_jobs():
                    if job.func_name == 'movies.tasks.retrain_professional_model':
                        job.delete()

                now = timezone.now()
                target_time = time(3, 0)
                scheduled_time = datetime.combine(now.date(), target_time)

                scheduled_time = timezone.make_aware(scheduled_time)

                if scheduled_time < now:
                    scheduled_time += timedelta(days=1)

                scheduler.schedule(
                    scheduled_time=scheduled_time,
                    func=retrain_professional_model,
                    interval=86400,
                    repeat=None,
                )
            except ImportError:
                pass
