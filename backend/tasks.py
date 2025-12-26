import os

from celery import shared_task, Celery
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from PIL import Image

THUMB_SIZES = [(64, 64), (128, 128), (256, 256)]

@shared_task
def send_email_task(subject, message, recipient_list, from_email=None):
    """
    Асинхронная задача отправки email.
    """
    if from_email is None:
        from_email = settings.EMAIL_HOST_USER

    msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    msg.send()

@shared_task
def generate_thumbnails(image_path, sizes=[(100, 100), (300, 300)]):
    """
    Асинхронная генерация миниатюр изображения. 
    """
    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
    if not os.path.exists(full_path):
        return f"File {full_path} does not exist"

    base, ext = os.path.splitext(full_path)
    for size in sizes:
        with Image.open(full_path) as img:
            img.thumbnail(size)
            thumb_path = f"{base}_{size[0]}x{size[1]}{ext}"
            img.save(thumb_path, quality=95, optimize=True)