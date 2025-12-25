from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


@shared_task
def send_email_task(subject, message, recipient_list, from_email=None):
    """
    Асинхронная задача отправки email.
    """
    if from_email is None:
        from_email = settings.EMAIL_HOST_USER

    msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    msg.send()