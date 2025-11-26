from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator
from model_utils.tracker import FieldTracker

STATE_CHOICES = (
    ("basket", "Статус корзины"),
    ("new", "Новый"),
    ("confirmed", "Подтвержден"),
    ("assembled", "Собран"),
    ("sent", "Отправлен"),
    ("delivered", "Доставлен"),
    ("canceled", "Отменен"),
)

USER_TYPE_CHOICES = (
    ("shop", "Магазин"),
    ("buyer", "Покупатель"),
)


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Создание и сохранение пользователя с email и паролем.
        """
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Стандартная модель пользователей.
    """

    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = "email"
    email = models.EmailField(_("email address"), unique=True)
    company = models.CharField(
        verbose_name="Компания", max_length=40, blank=True
    )
    position = models.CharField(
        verbose_name="Должность", max_length=40, blank=True
    )
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=150,
        help_text=_(
            "Required. 150 characters or fewer. "
            "Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    is_active = models.BooleanField(
        _("active"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    type = models.CharField(
        verbose_name="Тип пользователя",
        choices=USER_TYPE_CHOICES,
        max_length=5,
        default="buyer",
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Список пользователей"
        ordering = ("email",)


class Contact(models.Model):
    """
    Модель контактных данных для доставки.
    """

    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        related_name="contacts",
        on_delete=models.CASCADE,
    )
    city = models.CharField(verbose_name="Город", max_length=50)
    street = models.CharField(verbose_name="Улица", max_length=100)
    house = models.CharField(verbose_name="Дом", max_length=15, blank=True)
    structure = models.CharField(
        verbose_name="Корпус", max_length=15, blank=True
    )
    building = models.CharField(
        verbose_name="Строение", max_length=15, blank=True
    )
    apartment = models.CharField(
        verbose_name="Квартира", max_length=15, blank=True
    )
    phone = models.CharField(verbose_name="Телефон", max_length=20)

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Список контактов"

    def __str__(self):
        return f"{self.city}, {self.street}, {self.house}"


class Shop(models.Model):
    name = models.CharField(max_length=50, verbose_name="Название")
    url = models.URLField(verbose_name="Ссылка", null=True, blank=True)
    user = models.OneToOneField(
        User,
        verbose_name="Пользователь",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    state = models.BooleanField(
        verbose_name="Статус получения заказов", default=True
    )

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Список магазинов"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=40, verbose_name="Название")
    shops = models.ManyToManyField(
        Shop, verbose_name="Магазины", related_name="categories", blank=True
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Список категорий"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=80, verbose_name="Название")
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        related_name="products",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Список продуктов"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    model = models.CharField(max_length=80, verbose_name="Модель", blank=True)
    external_id = models.PositiveIntegerField(verbose_name="Внешний ИД")
    product = models.ForeignKey(
        Product,
        verbose_name="Продукт",
        related_name="product_infos",
        on_delete=models.CASCADE,
    )
    shop = models.ForeignKey(
        Shop,
        verbose_name="Магазин",
        related_name="product_infos",
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.PositiveIntegerField(verbose_name="Цена")
    price_rrc = models.PositiveIntegerField(
        verbose_name="Рекомендуемая розничная цена"
    )

    class Meta:
        verbose_name = "Информация о продукте"
        verbose_name_plural = "Информационный список о продуктах"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "shop", "external_id"],
                name="unique_product_info",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.shop.name}"


class Parameter(models.Model):
    name = models.CharField(max_length=40, verbose_name="Название")

    class Meta:
        verbose_name = "Имя параметра"
        verbose_name_plural = "Список имен параметров"
        ordering = ("-name",)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продукте",
        related_name="product_parameters",
        on_delete=models.CASCADE,
    )
    parameter = models.ForeignKey(
        Parameter,
        verbose_name="Параметр",
        related_name="product_parameters",
        on_delete=models.CASCADE,
    )
    value = models.CharField(verbose_name="Значение", max_length=100)

    class Meta:
        verbose_name = "Параметр"
        verbose_name_plural = "Список параметров"
        constraints = [
            models.UniqueConstraint(
                fields=["product_info", "parameter"],
                name="unique_product_parameter",
            ),
        ]

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


class Order(models.Model):
    """
    Модель заказа с исправленной связью с контактами доставки.
    """

    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        related_name="orders",
        on_delete=models.CASCADE,
    )
    contact = models.ForeignKey(
        Contact,
        verbose_name="Контакт доставки",
        related_name="orders",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    dt = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(
        verbose_name="Статус", choices=STATE_CHOICES, max_length=15
    )

    # Трекер для отслеживания изменений статуса
    tracker = FieldTracker(fields=["status"])

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"
        ordering = ("-dt",)
        indexes = [
            models.Index(fields=["status", "dt"]),
            models.Index(fields=["user", "dt"]),
        ]

    def __str__(self):
        return f"Заказ #{self.id} от {self.dt.strftime('%d.%m.%Y %H:%M')}"

    def get_total_cost(self):
        """
        Расчет общей стоимости заказа.
        """
        return sum(item.get_cost() for item in self.ordered_items.all())

    def save(self, *args, **kwargs):
        """
        Автоматическая установка статуса 'basket' для новых заказов.
        """
        if not self.id and not self.status:
            self.status = "basket"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """
    Модель элемента заказа с прямой связью с ProductInfo.
    """

    order = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        related_name="ordered_items",
        on_delete=models.CASCADE,
    )
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продукте",
        related_name="ordered_items",
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(
        verbose_name="Количество", default=1
    )

    class Meta:
        verbose_name = "Заказанная позиция"
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product_info"], name="unique_order_item"
            ),
        ]

    def clean(self):
        """
        Валидация данных.
        """
        if self.quantity <= 0:
            raise ValidationError(
                {"quantity": "Количество должно быть положительным числом"}
            )

        # Проверка доступного количества
        if (
            self.product_info.quantity < self.quantity
            and self.order.status != "basket"
        ):
            raise ValidationError(
                {
                    "quantity": f"Недостаточно товара в наличии. "
                    f"Доступно: {self.product_info.quantity}"
                }
            )

    def save(self, *args, **kwargs):
        """
        Вызов валидации при сохранении.
        """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_info.product.name} x {self.quantity}"

    def get_cost(self):
        """
        Расчет стоимости позиции заказа.
        """
        return self.product_info.price * self.quantity


class ConfirmEmailToken(models.Model):
    """
    Модель токена для подтверждения email.
    """

    user = models.ForeignKey(
        User,
        related_name="confirm_email_tokens",
        on_delete=models.CASCADE,
        verbose_name=_(
            "The User which is associated to this password reset token"
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("When was this token generated")
    )
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    class Meta:
        verbose_name = "Токен подтверждения Email"
        verbose_name_plural = "Токены подтверждения Email"

    @staticmethod
    def generate_key():
        """Генерация псевдослучайного кода."""
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return f"Password reset token for user {self.user}"


@receiver(post_save, sender=Order)
def order_created(sender, instance, created, **kwargs):
    """
    Отправка email при создании нового заказа.
    """
    try:
        if created and instance.status != "basket":
            send_mail(
                f"Заказ #{instance.id} создан",
                (
                    f"Ваш заказ #{instance.id} успешно создан. "
                    f"Статус: {instance.get_status_display()}"
                ),
                settings.EMAIL_HOST_USER,
                [instance.user.email],
                fail_silently=False,
            )
    except Exception as e:
        print(f"Ошибка отправки email для заказа {instance.id}: {e}")


@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, **kwargs):
    """
    Отправка email при изменении статуса заказа.
    """
    try:
        if (
            instance.tracker.has_changed("status")
            and instance.status != "basket"
        ):
            send_mail(
                f"Статус заказа #{instance.id} изменен",
                (
                    f"Статус вашего заказа #{instance.id} изменен на: "
                    f"{instance.get_status_display()}"
                ),
                settings.EMAIL_HOST_USER,
                [instance.user.email],
                fail_silently=False,
            )
    except Exception as e:
        print(
            f"Ошибка отправки email при изменении статуса "
            f"заказа {instance.id}: {e}"
        )


@receiver(post_save, sender=User)
def user_registered(sender, instance, created, **kwargs):
    """
    Отправка email с подтверждением регистрации.
    """
    try:
        if created and not instance.is_active:
            token = ConfirmEmailToken.objects.create(user=instance)
            send_mail(
                "Подтверждение регистрации",
                "Для подтверждения регистрации "
                f"используйте токен: {token.key}",
                settings.EMAIL_HOST_USER,
                [instance.email],
                fail_silently=False,
            )
    except Exception as e:
        print(
            f"Ошибка отправки email подтверждения для "
            f"пользователя {instance.email}: {e}"
        )
