import pytest
from django.apps import apps
from django.test import Client


@pytest.mark.django_db
class TestApplicationHealth:
    def test_core_apps_loaded(self):
        assert apps.ready is True

    def test_root_url_resolves(self):
        client = Client()
        response = client.get('/')
        assert response.status_code in [200, 404]
