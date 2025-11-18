from django.apps import AppConfig


class BackendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend"
    verbose_name = "Бэкенд"

    def ready(self):
        """
        импортируем сигналы
        """
        import backend.signals  # noqa: F401
