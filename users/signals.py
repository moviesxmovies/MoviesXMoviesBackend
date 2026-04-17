from allauth.socialaccount.signals import social_account_added
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .tasks import send_verification_email


@receiver(post_save, sender=User)
def send_verification_email_on_created(sender, instance: User, created: bool, **kwargs) -> None:
    if created and not instance.socialaccount_set.exists():
        send_verification_email.delay(instance)


@receiver(social_account_added)
def send_verification_email_on_oauth(sender, request, sociallogin, **kwargs) -> None:
    send_verification_email.delay(sociallogin.user)
