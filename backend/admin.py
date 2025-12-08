from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from backend.models import (
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


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    fieldsets = (
        (None, {"fields": ("email", "password", "type")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "company", "position")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "type"),
            },
        ),
    )

    list_display = (
        "email",
        "first_name",
        "last_name",
        "type",
        "is_staff",
        "is_active",
    )
    list_filter = ("type", "is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "first_name", "last_name", "company")
    ordering = ("email",)
    filter_horizontal = (
        "groups",
        "user_permissions",
    )


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "state", "user")
    list_filter = ("state",)
    search_fields = ("name", "url", "user__email")
    list_editable = ("state",)
    raw_id_fields = ("user",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    # Закомментируйте если нет поля slug
    # prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "id")
    list_filter = ("category",)
    search_fields = ("name", "category__name")
    raw_id_fields = ("category",)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ("product", "shop", "quantity", "price", "price_rrc")
    list_filter = ("shop",)
    search_fields = ("product__name", "shop__name")
    raw_id_fields = ("product", "shop")
    list_editable = ("quantity", "price", "price_rrc")


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ("product_info", "parameter", "value")
    list_filter = ("parameter",)
    search_fields = ("product_info__product__name", "parameter__name", "value")
    raw_id_fields = ("product_info", "parameter")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "dt", "contact", "total_amount")
    list_filter = ("status", "dt")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "id",
    )
    raw_id_fields = ("user",)
    list_editable = ("status",)
    date_hierarchy = "dt"
    
    def total_amount(self, obj):
        total = 0
        for item in obj.ordered_items.all():
            if hasattr(item, 'product_info') and item.product_info:
                total += item.quantity * item.product_info.price
        return f"{total:.2f}"
    total_amount.short_description = 'Total Amount'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    # Основные поля модели OrderItem
    list_display = ("order", "product_info", "quantity", "product_display", "shop_display", "price_display")
    list_filter = ("order__status",)
    search_fields = ("order__id", "product_info__product__name")
    raw_id_fields = ("order", "product_info")
    
    # Методы для отображения связанных данных
    def product_display(self, obj):
        if obj.product_info and obj.product_info.product:
            return obj.product_info.product.name
        return "N/A"
    product_display.short_description = 'Product'
    
    def shop_display(self, obj):
        if obj.product_info and obj.product_info.shop:
            return obj.product_info.shop.name
        return "N/A"
    shop_display.short_description = 'Shop'
    
    def price_display(self, obj):
        if obj.product_info:
            return obj.product_info.price
        return "N/A"
    price_display.short_description = 'Price'


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "phone", "id")
    list_filter = ("city",)
    search_fields = ("user__email", "city", "phone")
    raw_id_fields = ("user",)


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "key",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("user__email", "key")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)

    def has_change_permission(self, request, obj=None):
        return False