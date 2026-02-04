from time import sleep

import pytest
from django.utils import timezone

from genres.models import Genre


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
