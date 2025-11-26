from django.urls import include, path
from django_rest_passwordreset.views import (
    reset_password_confirm,
    reset_password_request_token,
)
from rest_framework.routers import DefaultRouter

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

# Создаем router для API v1
router = DefaultRouter()
router.register(r"shops", ShopView, basename="shop")
router.register(r"categories", CategoryView, basename="category")
router.register(r"products", ProductInfoView, basename="product")
router.register(r"basket", BasketView, basename="basket")
router.register(r"orders", OrderView, basename="order")
router.register(r"contacts", ContactView, basename="contact")

urlpatterns = [
    # API v1 с использованием router
    path("v1/", include(router.urls)),
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
