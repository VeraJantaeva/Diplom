from django.urls import path
from django_rest_passwordreset.views import (
    reset_password_confirm,
    reset_password_request_token,
)

from backend.views import (
    AccountDetails,
    BasketView,
    CategoryView,
    ConfirmAccount,
    LoginAccount,
    OrderView,
    PartnerOrders,
    PartnerState,
    ProductInfoView,
    RegisterAccount,
    ShopView,
)

from .views import (
    CartView,
    ConfirmEmailView,
    ContactView,
    LoginView,
    OrderConfirmView,
    OrderListView,
    PartnerUpdate,
    ProductListView,
    RegisterView,
)

app_name = "backend"
urlpatterns = [
    path("partner/update", PartnerUpdate.as_view(), name="partner-update"),
    path("partner/state", PartnerState.as_view(), name="partner-state"),
    path("partner/orders", PartnerOrders.as_view(), name="partner-orders"),
    path("user/register", RegisterAccount.as_view(), name="user-register"),
    path(
        "user/register/confirm",
        ConfirmAccount.as_view(),
        name="user-register-confirm",
    ),
    path("user/details", AccountDetails.as_view(), name="user-details"),
    path("user/contact", ContactView.as_view(), name="user-contact"),
    path("user/login", LoginAccount.as_view(), name="user-login"),
    path(
        "user/password_reset",
        reset_password_request_token,
        name="password-reset",
    ),
    path(
        "user/password_reset/confirm",
        reset_password_confirm,
        name="password-reset-confirm",
    ),
    path("categories", CategoryView.as_view(), name="categories"),
    path("shops", ShopView.as_view(), name="shops"),
    path("products", ProductInfoView.as_view(), name="shops"),
    path("basket", BasketView.as_view(), name="basket"),
    path("order", OrderView.as_view(), name="order"),
    # Аутентификация
    path("user/register/", RegisterView.as_view(), name="user-register-new"),
    path("user/login/", LoginView.as_view(), name="user-login-new"),
    path(
        "user/confirm-email/",
        ConfirmEmailView.as_view(),
        name="confirm-email"
    ),
    # Товары
    path("products/", ProductListView.as_view(), name="product-list"),
    # Корзина
    path("cart/", CartView.as_view(), name="cart"),
    # Контакты
    path("contacts/", ContactView.as_view(), name="contacts"),
    # Заказы
    path("order/confirm/", OrderConfirmView.as_view(), name="order-confirm"),
    path("orders/", OrderListView.as_view(), name="order-list"),
]
