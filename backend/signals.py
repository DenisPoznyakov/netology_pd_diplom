from typing import Type
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import ConfirmEmailToken, User

# Пользовательский сигнал для уведомления о новом зарегистрированном пользователе
new_user_registered = Signal()

# Пользовательский сигнал для уведомления о новом заказе (оформлении заказа покупателем)
new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Обработчик сигнала создания токена сброса пароля.
    Отправляет пользователю email с токеном для восстановления пароля.
    Реализует функционал восстановления пароля через API.
    """
    msg = EmailMultiAlternatives(
        # Тема письма
        f"Токен сброса пароля для {reset_password_token.user.email}",
        # Тело письма (токен)
        reset_password_token.key,
        # От кого
        settings.EMAIL_HOST_USER,
        # Кому
        [reset_password_token.user.email]
    )
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    """
    Обработчик сигнала сохранения нового пользователя.
    При создании неактивного пользователя (created and not is_active) генерирует токен подтверждения email
    и отправляет письмо с ключом подтверждения.
    Реализует подтверждение регистрации по email.
    """
    if created and not instance.is_active:
        # Генерируем или получаем существующий токен подтверждения
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)

        msg = EmailMultiAlternatives(
            # Тема письма
            f"Токен подтверждения email для {instance.email}",
            # Тело письма (ключ токена)
            token.key,
            # От кого
            settings.EMAIL_HOST_USER,
            # Кому
            [instance.email]
        )
        msg.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Обработчик пользовательского сигнала new_order.
    Отправляет покупателю уведомление на email о успешном оформлении заказа.
    Вызывается при переходе корзины в статус 'new'.
    """
    user = User.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        # Тема письма
        "Обновление статуса заказа",
        # Тело письма
        'Ваш заказ успешно сформирован и принят в обработку.',
        # От кого
        settings.EMAIL_HOST_USER,
        # Кому
        [user.email]
    )
    msg.send()