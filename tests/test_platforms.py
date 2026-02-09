import pytest

from platforms.serializers import PlatformSerializer

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
