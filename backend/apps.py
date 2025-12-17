from django.apps import AppConfig


class BackendConfig(AppAppConfig):
    """
    Конфигурация приложения backend.

    Указывает имя приложения и тип автоинкрементного поля по умолчанию.
    Метод ready() используется для инициализации сигналов приложения
    при запуске Django (импорт signals.py для регистрации обработчиков событий).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        """
        Выполняется при готовности приложения.

        Импортирует модуль signals.py, чтобы зарегистрировать сигналы
        (например, отправка email при создании заказа или смене статуса).
        Это обеспечивает автоматическую работу уведомлений и других обработчиков событий.
        """
        import backend.signals  # noqa