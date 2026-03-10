import secrets
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_rq import job
from django.utils.translation import gettext as _
from django.utils import translation
from users.models import User


def _send_email(user: User, subject_template: str, subject_kwargs: dict, template: str, extra_context: dict = None) -> None:
    """Activate the user's language, render and send an HTML email, then restore the language."""
    previous_language = translation.get_language()
    try:
        translation.activate(user.preferred_language or translation.get_default_language())
        context = {'user': user, **(extra_context or {})}
        email = EmailMessage(
            subject=_(subject_template).format(**subject_kwargs),
            body=render_to_string(template, context),
            to=[user.email],
        )
        email.content_subtype = 'html'
        email.send()
    finally:
        if previous_language:
            translation.activate(previous_language)
        else:
            translation.deactivate()


@job
def send_verification_email(user) -> None:
    """Generate a verification code and send it to the user via email."""
    user.verification_code = f'{secrets.randbelow(1000000):06d}'
    user.save()
    _send_email(
        user,
        subject_template='Verification of MoviesXMovies account for {username}',
        subject_kwargs={'username': user.username},
        template='users/email/verification-email.html',
    )


@job
def send_password_reset_email(user) -> None:
    """Generate a password reset code and send it to the user via email."""
    user.forgot_password_code = f'{secrets.randbelow(1000000):06d}'
    user.save()
    _send_email(
        user,
        subject_template='Password reset for MoviesXMovies account of {username}',
        subject_kwargs={'username': user.username},
        template='users/email/password-reset-email.html',
    )
