import secrets

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_rq import job


@job
def send_verification_email(user):
    user.verification_code = f'{secrets.randbelow(1000000):06d}'
    email = EmailMessage(
        subject=f'Verificación de MoviesXMovies de {user.username}',
        body=render_to_string('users/email/verification-email.html', {'user': user}),
        to=[user.email],
    )
    email.content_subtype = 'html'
    email.send()
    user.save()
