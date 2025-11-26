from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import ConfirmEmailToken, Order, User

# Объявляем кастомные сигналы
new_user_registered = Signal()
new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, **kwargs
):
    """
    Отправляем письмо с токеном для сброса пароля
    """
    try:
        msg = EmailMultiAlternatives(
            # title:
            f"Сброс пароля для {reset_password_token.user.email}",
            # message:
            f"Ваш токен для сброса пароля: {reset_password_token.key}",
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [reset_password_token.user.email],
        )
        msg.send()
    except Exception as e:
        print(f"Ошибка отправки email для сброса пароля: {e}")


@receiver(post_save, sender=User)
def new_user_registered_signal(
    sender: Type[User], instance: User, created: bool, **kwargs
):
    """
    Отправляем письмо с подтверждением почты
    при регистрации нового пользователя
    """
    if created and not instance.is_active:
        try:
            token = ConfirmEmailToken.objects.create(user=instance)
            msg = EmailMultiAlternatives(
                # title:
                f"Подтверждение email для {instance.email}",
                # message:
                f"Для подтверждения вашего email"
                f"используйте этот токен: {token.key}",
                # from:
                settings.EMAIL_HOST_USER,
                # to:
                [instance.email],
            )
            msg.send()
        except Exception as e:
            print(f"Ошибка отправки email подтверждения: {e}")


@receiver(new_order)
def new_order_signal(sender, **kwargs):
    """
    Отправляем письмо при создании нового заказа
    """
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            return

        user = User.objects.get(id=user_id)
        msg = EmailMultiAlternatives(
            # title:
            "Новый заказ создан",
            # message:
            "Ваш заказ был успешно создан и находится в обработке. "
            "Мы свяжемся с вами в ближайшее время.",
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [user.email],
        )
        msg.send()
    except User.DoesNotExist:
        print(f"Пользователь с id {user_id} не найден")
    except Exception as e:
        print(f"Ошибка отправки email о новом заказе: {e}")


@receiver(post_save, sender=Order)
def order_status_changed_signal(sender, instance, created, **kwargs):
    """
    Отправляем письмо при изменении статуса заказа
    """
    if not created:
        try:
            if hasattr(instance, "tracker") and instance.tracker.has_changed(
                "status"
            ):
                msg = EmailMultiAlternatives(
                    # title:
                    f"Обновление статуса заказа #{instance.id}",
                    # message:
                    f"Статус вашего заказа #{instance.id} "
                    f"изменен на: {instance.get_status_display()}",
                    # from:
                    settings.EMAIL_HOST_USER,
                    # to:
                    [instance.user.email],
                )
                msg.send()
        except Exception as e:
            print(f"Ошибка отправки email об изменении статуса заказа: {e}")
