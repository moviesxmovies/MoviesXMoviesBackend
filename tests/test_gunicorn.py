import sys
import os
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def reset_gunicorn_conf():
    """Force re-import of gunicorn_conf between tests."""
    yield
    if 'gunicorn_conf' in sys.modules:
        del sys.modules['gunicorn_conf']


def test_post_fork_sets_gunicorn_worker_env(monkeypatch):
    monkeypatch.delenv('GUNICORN_WORKER', raising=False)

    import gunicorn_conf
    gunicorn_conf.post_fork(MagicMock(), MagicMock())

    assert os.environ.get('GUNICORN_WORKER') == 'true'


def test_when_ready_cancels_existing_job_and_schedules():
    mock_job = MagicMock()
    mock_job.func_name = 'movies.tasks.retrain_professional_model'

    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = [mock_job]
    mock_server = MagicMock()

    with patch('django.setup'), \
         patch('django_rq.get_scheduler', return_value=mock_scheduler), \
         patch('movies.tasks.retrain_professional_model', MagicMock()):
        import gunicorn_conf
        gunicorn_conf.when_ready(mock_server)

    mock_scheduler.cancel.assert_called_once_with(mock_job)
    mock_scheduler.schedule.assert_called_once()
    mock_server.log.info.assert_called_once()


def test_when_ready_schedules_job_no_existing():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = []
    mock_server = MagicMock()

    with patch('django.setup'), \
         patch('django_rq.get_scheduler', return_value=mock_scheduler), \
         patch('movies.tasks.retrain_professional_model', MagicMock()):
        import gunicorn_conf
        gunicorn_conf.when_ready(mock_server)

    mock_scheduler.cancel.assert_not_called()
    mock_scheduler.schedule.assert_called_once()
    mock_server.log.info.assert_called_once()


def test_when_ready_adjusts_scheduled_time_if_past():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = []
    mock_server = MagicMock()
    captured = {}

    def capture_schedule(**kwargs):
        captured['scheduled_time'] = kwargs['scheduled_time']

    mock_scheduler.schedule.side_effect = capture_schedule

    with patch('django.setup'), \
         patch('django_rq.get_scheduler', return_value=mock_scheduler), \
         patch('movies.tasks.retrain_professional_model', MagicMock()):
        import gunicorn_conf
        gunicorn_conf.when_ready(mock_server)

    from django.utils import timezone
    assert captured['scheduled_time'] > timezone.now()


def test_when_ready_cancel_exception_is_silenced():
    mock_job = MagicMock()
    mock_job.func_name = 'movies.tasks.retrain_professional_model'

    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = [mock_job]
    mock_scheduler.cancel.side_effect = Exception('Redis error')
    mock_server = MagicMock()

    with patch('django.setup'), \
         patch('django_rq.get_scheduler', return_value=mock_scheduler), \
         patch('movies.tasks.retrain_professional_model', MagicMock()):
        import gunicorn_conf
        gunicorn_conf.when_ready(mock_server)

    mock_scheduler.schedule.assert_called_once()