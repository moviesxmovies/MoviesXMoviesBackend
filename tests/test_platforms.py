import pytest

from platforms.serializers import PlatformSerializer
from tests.conftest import PLATFORMS_LIST_URL

# ===========================================================================
#  MODELS
# ===========================================================================

# ===========================================================================
#  PLATFORM
# ===========================================================================


@pytest.mark.django_db
def test_platform_creation(platform_factory):
    platform = platform_factory()
    assert platform.name is not None
    assert platform.slug is not None
    assert platform.url is not None
    assert platform.deleted_at is None
    assert platform.created_at is not None
    assert platform.updated_at is not None


@pytest.mark.django_db
def test_platform_str(platform_factory):
    platform = platform_factory(name='Netflix')
    assert str(platform) == 'netflix'


# ===========================================================================
#  SERIALIZERS
# ===========================================================================
@pytest.mark.django_db
def test_platform_serializer(platform_factory):
    platform = platform_factory(name='Netflix', url='https://www.netflix.com')
    serialized = PlatformSerializer(platform).serialize()

    assert serialized['id'] == platform.pk
    assert serialized['name'] == 'Netflix'
    assert serialized['slug'] == 'netflix'
    assert serialized['url'] == 'https://www.netflix.com'


# ===========================================================================
#  VIEWS
# ===========================================================================
@pytest.mark.django_db
def test_platform_list_view(platform_factory, auth_client):
    platform_factory(name='Netflix', url='https://www.netflix.com')
    platform_factory(name='Hulu', url='https://www.hulu.com')

    response = auth_client.get(PLATFORMS_LIST_URL)
    assert response.status_code == 200
    data = response.json()

    assert 'Netflix' in {platform['name'] for platform in data}
    assert 'Hulu' in {platform['name'] for platform in data}
