from django.urls import include, path
from django_rest_passwordreset.views import (
    reset_password_confirm,
    reset_password_request_token,
)

from backend.views import (
    AccountDetails,
    BasketView,
    CategoryView,
    ConfirmAccount,
    ContactView,
    LoginAccount,
    OrderView,
    PartnerOrders,
    PartnerState,
    PartnerUpdate,
    ProductInfoView,
    RegisterAccount,
    ShopView,
)

app_name = "backend"

urlpatterns = [
    # Магазины
    path("v1/shops/", ShopView.as_view(), name="shops"),
    # Категории
    path("v1/categories/", CategoryView.as_view(), name="categories"),
    # Товары
    path("v1/products/", ProductInfoView.as_view(), name="products"),
    # Корзина
    path("v1/basket/", BasketView.as_view(), name="basket"),
    # Заказы
    path("v1/orders/", OrderView.as_view(), name="orders"),
    # Контакты
    path("v1/contacts/", ContactView.as_view(), name="contacts"),
    # Партнерские endpoints
    path("v1/partner/update/", PartnerUpdate.as_view(), name="partner-update"),
    path("v1/partner/state/", PartnerState.as_view(), name="partner-state"),
    path("v1/partner/orders/", PartnerOrders.as_view(), name="partner-orders"),
    # Аутентификация и пользовательские endpoints
    path("v1/user/register/", RegisterAccount.as_view(), name="user-register"),
    path(
        "v1/user/register/confirm/",
        ConfirmAccount.as_view(),
        name="user-register-confirm",
    ),
    path("v1/user/details/", AccountDetails.as_view(), name="user-details"),
    path("v1/user/login/", LoginAccount.as_view(), name="user-login"),
    # Сброс пароля
    path(
        "v1/user/password_reset/",
        reset_password_request_token,
        name="password-reset",
    ),
    path(
        "v1/user/password_reset/confirm/",
        reset_password_confirm,
        name="password-reset-confirm",
    ),
]