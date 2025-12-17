"""
netology_pd_diplom URL Configuration

Основной файл маршрутизации URL проекта.

Все запросы к API направляются в приложение backend через префикс /api/v1/.
Админка доступна по /admin/.

Подробная документация Django URL: 
https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    """
    Маршрут для административной панели Django.
    Доступна по адресу: http://127.0.0.1:8000/admin/
    Используется для управления моделями, пользователями и данными проекта.
    """
    path('admin/', admin.site.urls),

    """
    Все API-эндпоинты проекта собраны в приложении backend.
    Префикс /api/v1/ соответствует спецификации дипломного проекта.
    Включает:
    - Регистрацию, авторизацию, работу с профилем
    - Каталог товаров, корзину, заказы
    - Импорт/экспорт и управление заказами для поставщиков
    """
    path('api/v1/', include('backend.urls', namespace='backend')),
]