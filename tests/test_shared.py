import json
from http import HTTPStatus
from time import sleep

import pytest
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from genres.models import Genre
from reviews.serializers import ReviewSerializer
from shared.decorators import get_body, get_query_params, require_http_methods
from shared.serializers import BaseSerializer
from shared.utils import get_paginated_response
from shared.views import GoogleLogin


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
        request = factory.post('/api/auth/google/', HTTP_HOST='localhost:5173', secure=False)

        view = GoogleLogin()
        view.request = request

        expected_url = 'http://localhost:5173/accounts/google/login/callback/'
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
        def serialize_instance(self, instance):
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
        def serialize_instance(self, instance):
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
        def serialize_instance(self, instance):
            return {'id': instance.id, 'name': instance.name, 'url': self.build_url('/test-path/')}

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


# ===========================================================================
#  DECORATORS
# ===========================================================================

# ===========================================================================
#  REQUIRE HTTP METHODS
# ===========================================================================


@pytest.fixture
def mock_view_require_http_methods():
    """Creates a dummy view function decorated with @require_http_methods(['GET', 'POST']) for testing."""

    @require_http_methods(['GET', 'POST'])
    def view(request):
        return JsonResponse({'data': 'success'}, status=HTTPStatus.OK)

    return view


@pytest.mark.django_db
def test_allowed_methods(rf, mock_view_require_http_methods):
    # Test GET
    request_get = rf.get('/')
    response_get = mock_view_require_http_methods(request_get)
    assert response_get.status_code == HTTPStatus.OK
    data = json.loads(response_get.content)
    assert data == {'data': 'success'}

    # Test POST
    request_post = rf.post('/')
    response_post = mock_view_require_http_methods(request_post)
    assert response_post.status_code == HTTPStatus.OK
    data = json.loads(response_post.content)
    assert data == {'data': 'success'}


@pytest.mark.django_db
def test_disallowed_method(rf, mock_view_require_http_methods):
    request = rf.delete('/')
    response = mock_view_require_http_methods(request)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    data = json.loads(response.content)
    assert data == {'error': 'Method not allowed'}


@pytest.mark.django_db
def test_put_is_also_disallowed(rf, mock_view_require_http_methods):
    request = rf.put('/')
    response = mock_view_require_http_methods(request)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    data = json.loads(response.content)
    assert data == {'error': 'Method not allowed'}


# =================================================================
#  GET QUERY PARAMS
# =================================================================
@pytest.fixture
def mock_view_get_query_params():
    """Creates a dummy view function decorated with @get_query_params for testing."""

    @get_query_params('search', 'page')
    def view(request, *args, **kwargs):
        return JsonResponse(kwargs, status=HTTPStatus.OK)

    return view


@pytest.mark.django_db
def test_params_injection_success(rf, mock_view_get_query_params):

    params = {'search': 'django', 'page': '5'}
    request = rf.get('/', params)

    response = mock_view_get_query_params(request)

    data = json.loads(response.content)

    assert response.status_code == HTTPStatus.OK
    assert data['search'] == 'django'
    assert data['page'] == '5'


@pytest.mark.django_db
def test_params_not_provided_are_none(rf, mock_view_get_query_params):

    request = rf.get('/')
    response = mock_view_get_query_params(request)
    data = json.loads(response.content)

    assert response.status_code == HTTPStatus.OK
    assert data['search'] is None
    assert data['page'] is None


@pytest.mark.django_db
def test_extra_params_are_ignored_by_decorator(rf, mock_view_get_query_params):

    request = rf.get('/', {'search': 'test', 'extra_param': 'hack'})
    response = mock_view_get_query_params(request)
    data = json.loads(response.content)

    assert data['search'] == 'test'
    assert 'extra_param' not in data


# =================================================================
#  GET BODY
# =================================================================
class MockMovieModel:
    """Mock model class for testing get_body decorator with model instantiation."""

    def __init__(self, title, year):
        self.title = title
        self.year = year


@pytest.fixture
def mock_view_get_body_with_model():
    """View that uses get_body and converts the JSON to an instance of MockMovieModel."""

    @get_body(MockMovieModel, required_fields=['title', 'year'])
    def view(request, mockmoviemodel=None):
        return JsonResponse({'title': mockmoviemodel.title, 'year': mockmoviemodel.year})

    return view


@pytest.fixture
def mock_view_get_body_no_model():
    """View that uses get_body without a model, injecting a dictionary in 'body'."""

    @get_body(None, required_fields=['name'])
    def view(request, body=None):
        return JsonResponse(body)

    return view


@pytest.mark.django_db
def test_get_body_success_model_injection(rf, mock_view_get_body_with_model):
    payload = {'title': 'The Matrix', 'year': 1999}
    request = rf.post('/', data=json.dumps(payload), content_type='application/json')

    response = mock_view_get_body_with_model(request)
    data = json.loads(response.content)

    assert response.status_code == HTTPStatus.OK
    assert data['title'] == 'The Matrix'
    assert data['year'] == 1999


@pytest.mark.django_db
def test_get_body_success_dictionary_injection(rf, mock_view_get_body_no_model):
    payload = {'name': 'Inception'}
    request = rf.post('/', data=json.dumps(payload), content_type='application/json')

    response = mock_view_get_body_no_model(request)
    data = json.loads(response.content)

    assert response.status_code == HTTPStatus.OK
    assert data['name'] == 'Inception'


@pytest.mark.django_db
def test_get_body_error_missing_fields(rf, mock_view_get_body_with_model):
    payload = {'title': 'Interstellar'}
    request = rf.post('/', data=json.dumps(payload), content_type='application/json')

    response = mock_view_get_body_with_model(request)
    data = json.loads(response.content)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert data['error'] == 'Missing required fields'


@pytest.mark.django_db
def test_get_body_error_invalid_json(rf, mock_view_get_body_no_model):
    request = rf.post('/', data='{"name": "Broken JSON', content_type='application/json')

    response = mock_view_get_body_no_model(request)
    data = json.loads(response.content)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert data['error'] == 'Invalid JSON body'


# =================================================================
#  GET PAGINATED RESPONSE
# =================================================================


@pytest.mark.django_db
def test_get_paginated_response(movie_factory, auth_client, user_factory):
    movie = movie_factory(title='Inception')
    for i in range(15):
        user = user_factory()
        movie.reviews.create(
            title=f'Review {i}', content='Great movie!', is_positive=True, user=user
        )
    response = get_paginated_response(
        movie.reviews.all().order_by('-created_at'),
        ReviewSerializer,
        None,
        page='1',
        limit='10',
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    assert 'results' in data
    assert len(data['results']) == 10
    assert data.get('count') == 15
    assert data['has_next'] is True
    assert data['has_previous'] is False
    assert data['current_page'] == 1
    assert data['total_pages'] == 2
