from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """
    A custom QuerySet that implements soft deletion by filtering out objects with a non-null 'deleted_at' field.
    """

    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """
    An abstract base class model that provides self-updating
    'created_at' and 'updated_at' fields to any model that inherits from it.
    Also includes a 'deleted_at' field for soft deletion.

    Attributes:
        created_at (models.DateTimeField): The date and time when the record was created.
        updated_at (models.DateTimeField): The date and time when the record was last updated.
        deleted_at (models.DateTimeField): The date and time when the record was soft deleted.

    Note:
        This is an abstract model and will not create a database table.

    """

    class Meta:
        abstract = True

    objects = SoftDeleteManager()
    includes_all = models.Manager()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True, default=None)

    def delete(self, **kwargs):
        """Soft delete the object by setting 'deleted_at' timestamp."""
        self.deleted_at = timezone.now()
        self.save()

        self._cascade_soft_delete()

    def _cascade_soft_delete(self):
        for related in self._meta.related_objects:
            if related.on_delete == models.CASCADE:
                related.related_model.objects.filter(**{related.field.name: self}).update(
                    deleted_at=timezone.now()
                )

        ct = ContentType.objects.get_for_model(self)
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if hasattr(field, 'ct_field'):
                    object_id_field = field.fk_field
                    ct_field = field.ct_field
                    model.objects.filter(**{ct_field: ct, object_id_field: self.pk}).update(
                        deleted_at=timezone.now()
                    )

    def hard_delete(self, **kwargs):
        """Permanently delete the object from the database."""
        super().delete(**kwargs)

    def restore(self):
        """Restore a soft-deleted object by clearing 'deleted_at'."""
        self.deleted_at = None
        self.save()
