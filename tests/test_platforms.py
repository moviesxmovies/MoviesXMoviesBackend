import pytest

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