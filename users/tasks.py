import secrets
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_rq import job


@job
def send_verification_email(user) -> None:
    """Generate a verification code and send it to the user via email.

    Generates a cryptographically secure 6-digit code, assigns it to
    ``user.verification_code``, persists the user, and dispatches an HTML
    email rendered from ``users/email/verification-email.html``.

    Args:
        user (User): The user instance to verify. Must have ``username``,
            ``email``, and ``verification_code`` fields.
    """
    user.verification_code = f'{secrets.randbelow(1000000):06d}'
    email = EmailMessage(
        subject=f'Verificación de MoviesXMovies de {user.username}',
        body=render_to_string('users/email/verification-email.html', {'user': user}),
        to=[user.email],
    )
    email.content_subtype = 'html'
    user.save()
    email.send()


@job
def send_password_reset_email(user) -> None:
    """Generate a password reset code and send it to the user via email.

    Generates a cryptographically secure 6-digit code, assigns it to
    ``user.forgot_password_code``, persists the user, and dispatches an HTML
    email rendered from ``users/email/password-reset-email.html``.

    Args:
        user (User): The user instance requesting a password reset. Must have
            ``username``, ``email``, and ``forgot_password_code`` fields.
    """
    user.forgot_password_code = f'{secrets.randbelow(1000000):06d}'
    email = EmailMessage(
        subject=f'Restablecimiento de contraseña de MoviesXMovies de {user.username}',
        body=render_to_string('users/email/password-reset-email.html', {'user': user}),
        to=[user.email],
    )
    email.content_subtype = 'html'
    user.save()
    email.send()
