from time import sleep

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from genres.models import Genre
from shared.views import GoogleLogin

from shared.serializers import BaseSerializer
from django.http import JsonResponse


# =================================================================
# BASE MODEL TESTS
# =================================================================
@pytest.mark.django_db
class TestBaseModel:
    def test_soft_delete_sets_timestamp(self):
        obj = Genre.objects.create(name='Test', slug='test-genre')
        obj.delete()

        obj.refresh_from_db()
        assert obj.deleted_at is not None
        assert isinstance(obj.deleted_at, timezone.datetime)

    def test_objects_manager_excludes_deleted(self):
        Genre.objects.create(name='Visible', slug='visible-genre')
        deleted_obj = Genre.objects.create(name='Invisible', slug='invisible-genre')
        deleted_obj.delete()

        assert Genre.objects.count() == 1
        assert 'Visible' in Genre.objects.values_list('name', flat=True)

    def test_includes_all_manager_shows_everything(self):
        Genre.objects.create(name='Active', slug='active-genre')
        deleted = Genre.objects.create(name='Deleted', slug='deleted-genre')
        deleted.delete()

        assert Genre.includes_all.count() == 2

    def test_restore_functionality(self):
        obj = Genre.objects.create(name='I Always Come Back', slug='come-back-genre')
        obj.delete()
        assert Genre.objects.count() == 0

        obj.restore()
        assert obj.deleted_at is None
        assert Genre.objects.count() == 1

    def test_hard_delete_permanently_removes(self):
        obj = Genre.objects.create(name='bye', slug='bye-genre')
        obj.hard_delete()

        assert Genre.includes_all.count() == 0

    def test_bulk_delete_uses_soft_delete(self):
        Genre.objects.create(name='Batch 1', slug='batch-1')
        Genre.objects.create(name='Batch 2', slug='batch-2')

        Genre.objects.all().delete()
        assert Genre.objects.count() == 0
        assert Genre.includes_all.count() == 2
        assert Genre.includes_all.filter(deleted_at__isnull=False).count() == 2

    def test_bulk_hard_delete_permanently_removes(self):
        Genre.objects.create(name='Permanent 1', slug='permanent-1')
        Genre.objects.create(name='Permanent 2', slug='permanent-2')

        Genre.objects.all().hard_delete()
        assert Genre.includes_all.count() == 0

    def test_timestamps_update(self):
        obj = Genre.objects.create(name='Original', slug='original-genre')
        old_update = obj.updated_at

        sleep(0.1)
        obj.name = 'Modificado'
        obj.save()

        assert obj.updated_at > old_update


# =================================================================
# VIEWS
# =================================================================

# =================================================================
# GOOGLELOGIN
# =================================================================


@pytest.mark.django_db
class TestGoogleLoginView:
    def test_callback_url_logic(self):
        factory = APIRequestFactory()
        request = factory.post('/api/auth/google/', HTTP_HOST='mxm-backend.com', secure=True)

        view = GoogleLogin()
        view.request = request

        expected_url = 'https://mxm-backend.com/accounts/google/login/callback/'
        assert view.callback_url == expected_url

    def test_callback_url_http_fallback(self):
        factory = APIRequestFactory()
        request = factory.post('/api/auth/google/', HTTP_HOST='localhost:8000', secure=False)

        view = GoogleLogin()
        view.request = request

        expected_url = 'http://localhost:8000/accounts/google/login/callback/'
        assert view.callback_url == expected_url

# =================================================================
#  SERIALIZERS
# =================================================================

@pytest.mark.django_db
def test_base_serializer():
    class TestModel:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class TestSerializer(BaseSerializer):
        def serialize_instance(self,instance):
            return {
                'id': instance.id,
                'name': instance.name,
            }

    test_instance = TestModel(id=1, name='Test Name')
    serializer = TestSerializer(test_instance)
    serialized_data = serializer.serialize()

    assert serialized_data['id'] == 1
    assert serialized_data['name'] == 'Test Name'

@pytest.mark.django_db
def test_base_serializer_json():
    class TestModel:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class TestSerializer(BaseSerializer):
        def serialize_instance(self,instance):
            return {
                'id': instance.id,
                'name': instance.name,
            }

    test_instance = TestModel(id=2, name='Another Test')
    serializer = TestSerializer(test_instance)
    json_data = serializer.to_json()
    json_response = serializer.json_response()

    assert json_data == '{"id": 2, "name": "Another Test"}'
    assert json_response.status_code == 200
    assert json_response.content == b'{"id": 2, "name": "Another Test"}'


@pytest.mark.django_db
def test_base_serializer_request_img():
    class TestModel:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class TestSerializer(BaseSerializer):
        def serialize_instance(self,instance):
            return {
                'id': instance.id,
                'name': instance.name,
                'url': self.build_url('/test-path/')
            }

    factory = APIRequestFactory()
    request = factory.get('/test/', HTTP_HOST='localhost:8000', secure=False)

    test_instance = TestModel(id=3, name='URL Test')
    serializer = TestSerializer(test_instance, request=request)
    serialized_data = serializer.serialize()

    assert serialized_data['url'] == 'http://localhost:8000/test-path/'

@pytest.mark.django_db
def test_base_serializer_not_implemented():
    class TestModel:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class IncompleteSerializer(BaseSerializer):
        pass

    test_instance = TestModel(id=4, name='Not Implemented Test')
    serializer = IncompleteSerializer(test_instance)

    with pytest.raises(NotImplementedError):
        serializer.serialize()
