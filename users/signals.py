from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .tasks import send_verification_email


@receiver(post_save, sender=User)
def send_verification_email_on_created(sender, instance: User, created: bool, **kwargs) -> None:
    """Send a verification email when a new User instance is created.

    Connected to the ``post_save`` signal of ``User``. Dispatches
    ``send_verification_email`` asynchronously via RQ only on creation,
    not on subsequent saves.

    Args:
        sender: The model class that sent the signal (``User``).
        instance (User): The user instance that was saved.
        created (bool): ``True`` if a new record was created, ``False``
            if an existing record was updated.
        **kwargs: Additional keyword arguments passed by the signal.
    """
    if created:
        send_verification_email.delay(instance)
