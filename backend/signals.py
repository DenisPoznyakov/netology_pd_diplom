from typing import Type

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import ConfirmEmailToken, User
from backend.tasks import send_email_task  # ← Импорт асинхронной задачи

# Пользовательские сигналы
new_user_registered = Signal()
new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Обработчик сигнала создания токена сброса пароля.
    Отправляет пользователю email с токеном для восстановления пароля (асинхронно через Celery).
    Реализует функционал восстановления пароля через API.
    """
    send_email_task.delay(
        subject=f"Токен сброса пароля для {reset_password_token.user.email}",
        message=reset_password_token.key,
        recipient_list=[reset_password_token.user.email],
        from_email=settings.EMAIL_HOST_USER
    )


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    """
    Обработчик сигнала сохранения нового пользователя.
    При создании неактивного пользователя генерирует токен подтверждения email
    и отправляет письмо с ключом подтверждения (асинхронно через Celery).
    Реализует подтверждение регистрации по email.
    """
    if created and not instance.is_active:
        # Генерируем или получаем существующий токен подтверждения
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)

        send_email_task.delay(
            subject=f"Токен подтверждения email для {instance.email}",
            message=token.key,
            recipient_list=[instance.email],
            from_email=settings.EMAIL_HOST_USER
        )


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Обработчик пользовательского сигнала new_order.
    Отправляет покупателю уведомление на email о успешном оформлении заказа (асинхронно через Celery).
    Вызывается при переходе корзины в статус 'new'.
    """
    user = User.objects.get(id=user_id)

    send_email_task.delay(
        subject="Обновление статуса заказа",
        message='Ваш заказ успешно сформирован и принят в обработку.',
        recipient_list=[user.email],
        from_email=settings.EMAIL_HOST_USER
    )