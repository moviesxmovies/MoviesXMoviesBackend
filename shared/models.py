from django.db import models


class Timestamps(models.Model):
    """
    An abstract base class model that provides self-updating
    'created_at' and 'updated_at' fields to any model that inherits from it.

    Attributes:
        created_at (DateTimeField): The date and time when the record was created.
        updated_at (DateTimeField): The date and time when the record was last updated.

    Note:
        This is an abstract model and will not create a database table.

    """

    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
