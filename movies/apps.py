import logging
import os
import sys
from datetime import datetime, time, timedelta

from django.apps import AppConfig
from django.utils import timezone

logger = logging.getLogger(__name__)


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    def ready(self):
        is_forced = os.environ.get('FORCE_RQ_SCHEDULER') == 'true'

        if 'collectstatic' in sys.argv:
            logger.info('Collectstatic command detected. Skipping job scheduling.')
            return

        if ('test' in sys.argv or 'pytest' in sys.modules) and not is_forced:
            logger.info('Test environment detected. Skipping job scheduling.')
            return

        if os.environ.get('GUNICORN_WORKER') == 'true':
            logger.info('Gunicorn worker process. Skipping job scheduling.')
            return

        if not is_forced and os.environ.get('RUN_MAIN') != 'true' and not any('gunicorn' in arg for arg in sys.argv):
            logger.info('Not the main process. Skipping job scheduling.')
            return


        try:
            import django_rq

            from .tasks import retrain_professional_model

            scheduler = django_rq.get_scheduler('default')

            for job in scheduler.get_jobs():
                if job.func_name == 'movies.tasks.retrain_professional_model':
                    try:
                        scheduler.cancel(job)
                        logger.info(f'Canceled existing job: {job}')
                    except Exception as e:
                        logger.error(f'Error occurred while canceling job: {e}')

            now = timezone.now()
            target_time = time(3, 0)
            scheduled_time = datetime.combine(now.date(), target_time)
            scheduled_time = timezone.make_aware(scheduled_time)

            if scheduled_time < now:
                scheduled_time += timedelta(days=1)
                logger.info(
                    f'Scheduled time is in the past. Adjusting to next day: {scheduled_time}'
                )

            job_scheduled = scheduler.schedule(
                scheduled_time=scheduled_time,
                func=retrain_professional_model,
                interval=86400,
                repeat=None,
            )
            logger.info(f'Job scheduled: {job_scheduled}')

        except ImportError:
            logger.error('Error occurred while importing django_rq')
