from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from requests import get
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from setuptools._distutils.util import strtobool
from ujson import loads as load_json
from yaml import Loader
from yaml import load as load_yaml

from .models import (
    Category,
    ConfirmEmailToken,
    Contact,
    Order,
    OrderItem,
    Parameter,
    Product,
    ProductInfo,
    ProductParameter,
    Shop,
    User,
)
from .serializers import (
    CategorySerializer,
    ContactSerializer,
    OrderItemCreateSerializer,
    OrderSerializer,
    ProductInfoSerializer,
    ProductSerializer,
    ShopSerializer,
    UserRegisterSerializer,
    UserSerializer,
)
from .signals import new_order


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    def post(self, request, *args, **kwargs):
        if {
            "first_name",
            "last_name",
            "email",
            "password",
            "company",
            "position",
        }.issubset(request.data):
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse(
                    {"Status": False, "Errors": {"password": error_array}}
                )
            else:
                user_serializer = UserRegisterSerializer(data=request.data)
                if user_serializer.is_valid():
                    user_serializer.save()
                    return JsonResponse({"Status": True})
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": user_serializer.errors}
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    def post(self, request, *args, **kwargs):
        if {"email", "token"}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(
                user__email=request.data["email"], key=request.data["token"]
            ).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({"Status": True})
            else:
                return JsonResponse(
                    {
                        "Status": False,
                        "Errors": "Неправильно указан токен или email",
                    }
                )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class AccountDetails(APIView):
    """
    Для управления данными аккаунта
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if "password" in request.data:
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse(
                    {"Status": False, "Errors": {"password": error_array}}
                )
            else:
                request.user.set_password(request.data["password"])
                request.user.save()

        user_serializer = UserSerializer(
            request.user, data=request.data, partial=True
        )
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({"Status": True})
        else:
            return JsonResponse(
                {"Status": False, "Errors": user_serializer.errors}
            )


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    def post(self, request, *args, **kwargs):
        if {"email", "password"}.issubset(request.data):
            user = authenticate(
                request,
                username=request.data["email"],
                password=request.data["password"],
            )

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({"Status": True, "Token": token.key})
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": "Аккаунт не активирован"}
                    )

            return JsonResponse(
                {"Status": False, "Errors": "Неверный email или пароль"}
            )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    permission_classes = [AllowAny]


class ProductInfoView(APIView):
    """
    Для поиска товаров
    """

    def get(self, request: Request, *args, **kwargs):
        query = Q(shop__state=True)
        shop_id = request.query_params.get("shop_id")
        category_id = request.query_params.get("category_id")

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        queryset = (
            ProductInfo.objects.filter(query)
            .select_related("shop", "product__category")
            .prefetch_related("product_parameters__parameter")
            .distinct()
        )

        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class BasketView(APIView):
    """
    Для управления корзиной
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        basket = (
            Order.objects.filter(user_id=request.user.id, status="basket")
            .prefetch_related(
                "ordered_items__product__category", "ordered_items__shop"
            )
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .first()
        )

        if basket:
            serializer = OrderSerializer(basket)
            return Response(serializer.data)
        else:
            return Response({"Status": False, "Message": "Корзина пуста"})

    def post(self, request, *args, **kwargs):
        items_string = request.data.get("items")
        if items_string:
            try:
                items_dict = load_json(items_string)
            except ValueError:
                return JsonResponse(
                    {"Status": False, "Errors": "Неверный формат запроса"}
                )
            else:
                basket, _ = Order.objects.get_or_create(
                    user_id=request.user.id, status="basket"
                )
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({"order": basket.id})
                    serializer = OrderItemCreateSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse(
                                {"Status": False, "Errors": str(error)}
                            )
                        else:
                            objects_created += 1
                    else:
                        return JsonResponse(
                            {"Status": False, "Errors": serializer.errors}
                        )

                return JsonResponse(
                    {"Status": True, "Создано объектов": objects_created}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def delete(self, request, *args, **kwargs):
        items_string = request.data.get("items")
        if items_string:
            items_list = items_string.split(",")
            basket, _ = Order.objects.get_or_create(
                user_id=request.user.id, status="basket"
            )
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse(
                    {"Status": True, "Удалено объектов": deleted_count}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def put(self, request, *args, **kwargs):
        items_string = request.data.get("items")
        if items_string:
            try:
                items_dict = load_json(items_string)
            except ValueError:
                return JsonResponse(
                    {"Status": False, "Errors": "Неверный формат запроса"}
                )
            else:
                basket, _ = Order.objects.get_or_create(
                    user_id=request.user.id, status="basket"
                )
                objects_updated = 0
                for order_item in items_dict:
                    if isinstance(order_item.get("id"), int) and isinstance(
                        order_item.get("quantity"), int
                    ):
                        updated = OrderItem.objects.filter(
                            order_id=basket.id, id=order_item["id"]
                        ).update(quantity=order_item["quantity"])
                        objects_updated += updated

                return JsonResponse(
                    {"Status": True, "Обновлено объектов": objects_updated}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class PartnerUpdate(APIView):
    """
    Для обновления прайса от поставщика
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )

        url = request.data.get("url")
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({"Status": False, "Error": str(e)})
            else:
                try:
                    stream = get(url).content
                    data = load_yaml(stream, Loader=Loader)

                    shop, _ = Shop.objects.get_or_create(
                        name=data["shop"], user_id=request.user.id
                    )

                    for category in data["categories"]:
                        category_object, _ = Category.objects.get_or_create(
                            id=category["id"], name=category["name"]
                        )
                        category_object.shops.add(shop.id)

                    ProductInfo.objects.filter(shop_id=shop.id).delete()

                    for item in data["goods"]:
                        product, _ = Product.objects.get_or_create(
                            name=item["name"], category_id=item["category"]
                        )

                        product_info = ProductInfo.objects.create(
                            product_id=product.id,
                            external_id=item["id"],
                            model=item.get("model", ""),
                            price=item["price"],
                            price_rrc=item["price_rrc"],
                            quantity=item["quantity"],
                            shop_id=shop.id,
                        )

                        for name, value in item["parameters"].items():
                            parameter_object, _ = (
                                Parameter.objects.get_or_create(name=name)
                            )
                            ProductParameter.objects.create(
                                product_info_id=product_info.id,
                                parameter_id=parameter_object.id,
                                value=value,
                            )

                    return JsonResponse({"Status": True})

                except Exception as e:
                    return JsonResponse(
                        {
                            "Status": False,
                            "Error": f"Ошибка обработки данных: {str(e)}",
                        }
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class PartnerState(APIView):
    """
    Для управления статусом поставщика
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )

        shop = getattr(request.user, "shop", None)
        if shop:
            serializer = ShopSerializer(shop)
            return Response(serializer.data)
        else:
            return JsonResponse(
                {"Status": False, "Error": "Магазин не найден"}
            )

    def post(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )

        state = request.data.get("state")
        if state is not None:
            try:
                Shop.objects.filter(user_id=request.user.id).update(
                    state=strtobool(state)
                )
                return JsonResponse({"Status": True})
            except ValueError as error:
                return JsonResponse({"Status": False, "Errors": str(error)})

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class PartnerOrders(APIView):
    """
    Для получения заказов поставщиками
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.type != "shop":
            return JsonResponse(
                {"Status": False, "Error": "Только для магазинов"}, status=403
            )

        orders = (
            Order.objects.filter(
                ordered_items__product_info__shop__user_id=request.user.id
            )
            .exclude(status="basket")
            .prefetch_related(
                "ordered_items__product__category", "ordered_items__shop"
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
    Для управления контактами
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contacts = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {"type", "value"}.issubset(request.data):
            data = request.data.copy()
            data["user"] = request.user.id

            serializer = ContactSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({"Status": True})
            else:
                return JsonResponse(
                    {"Status": False, "Errors": serializer.errors}
                )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def delete(self, request, *args, **kwargs):
        items_string = request.data.get("items")
        if items_string:
            items_list = items_string.split(",")
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse(
                    {"Status": True, "Удалено объектов": deleted_count}
                )
        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )

    def put(self, request, *args, **kwargs):
        contact_id = request.data.get("id")
        if contact_id and contact_id.isdigit():
            contact = Contact.objects.filter(
                id=contact_id, user_id=request.user.id
            ).first()
            if contact:
                serializer = ContactSerializer(
                    contact, data=request.data, partial=True
                )
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({"Status": True})
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": serializer.errors}
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class OrderView(APIView):
    """
    Для получения и размещения заказов
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        orders = (
            Order.objects.filter(user_id=request.user.id)
            .exclude(status="basket")
            .prefetch_related(
                "ordered_items__product__category", "ordered_items__shop"
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {"id", "contact"}.issubset(request.data):
            order_id = request.data["id"]
            contact_id = request.data["contact"]

            if isinstance(order_id, int) or (
                isinstance(order_id, str) and order_id.isdigit()
            ):
                try:
                    order_id = int(order_id)
                    with transaction.atomic():
                        order = Order.objects.get(
                            id=order_id,
                            user_id=request.user.id,
                            status="basket",
                        )
                        order.contact_id = contact_id
                        order.status = "new"
                        order.save()

                        new_order.send(
                            sender=self.__class__, user_id=request.user.id
                        )
                        return JsonResponse({"Status": True})

                except Order.DoesNotExist:
                    return JsonResponse(
                        {"Status": False, "Errors": "Заказ не найден"}
                    )
                except IntegrityError:
                    return JsonResponse(
                        {
                            "Status": False,
                            "Errors": "Неправильно указаны аргументы",
                        }
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


class ProductListView(generics.ListAPIView):
    """
    Список товаров
    """

    queryset = Product.objects.prefetch_related(
        "product_infos__shop", "product_infos__product_parameters__parameter"
    )
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        shop_id = self.request.query_params.get("shop_id")
        if shop_id:
            queryset = queryset.filter(product_infos__shop_id=shop_id)

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset.distinct()


class OrderConfirmView(APIView):
    """
    Подтверждение заказа
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        contact_id = request.data.get("contact_id")
        if not contact_id:
            return Response(
                {"Status": False, "Error": "Не указан контакт"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                basket = Order.objects.get(user=request.user, status="basket")

                if not basket.ordered_items.exists():
                    return Response(
                        {"Status": False, "Error": "Корзина пуста"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                for item in basket.ordered_items.all():
                    product_info = ProductInfo.objects.filter(
                        product=item.product, shop=item.shop
                    ).first()

                    if not product_info:
                        return Response(
                            {
                                "Status": False,
                                "Error": (
                                    f"Товар {item.product.name} не найден "
                                    f"в магазине {item.shop.name}"
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if item.quantity > product_info.quantity:
                        return Response(
                            {
                                "Status": False,
                                "Error": (
                                    f"Недостаточно товара {item.product.name}."
                                    f" Доступно: {product_info.quantity}"
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                basket.status = "new"
                basket.contact_id = contact_id
                basket.save()

                for item in basket.ordered_items.all():
                    ProductInfo.objects.filter(
                        product=item.product, shop=item.shop
                    ).update(quantity=F("quantity") - item.quantity)

                return Response(
                    {
                        "Status": True,
                        "Message": "Заказ подтвержден",
                        "OrderId": basket.id,
                    }
                )

        except Order.DoesNotExist:
            return Response(
                {"Status": False, "Error": "Корзина не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Contact.DoesNotExist:
            return Response(
                {"Status": False, "Error": "Контакт не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )


class OrderListView(generics.ListAPIView):
    """
    Просмотр списка заказов
    """

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .exclude(status="basket")
            .prefetch_related("ordered_items__product", "ordered_items__shop")
            .order_by("-dt")
        )


class ConfirmEmailView(APIView):
    """
    Подтверждение email
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        token = request.data.get("token")

        if not email or not token:
            return Response(
                {"Status": False, "Error": "Не указаны email и токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
            confirm_token = ConfirmEmailToken.objects.get(user=user, key=token)

            user.is_active = True
            user.save()
            confirm_token.delete()

            return Response({"Status": True, "Message": "Email подтвержден"})

        except User.DoesNotExist:
            return Response(
                {"Status": False, "Error": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ConfirmEmailToken.DoesNotExist:
            return Response(
                {"Status": False, "Error": "Неверный токен"},
                status=status.HTTP_400_BAD_REQUEST,
            )
