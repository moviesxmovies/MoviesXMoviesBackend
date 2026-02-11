from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .tasks import send_verification_email


@receiver(post_save, sender=User)
def send_verification_email_on_created(sender, instance, created, **kwargs):
    if created:
        send_verification_email.delay(instance)
