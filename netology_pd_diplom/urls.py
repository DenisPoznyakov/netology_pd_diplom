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
    # Административная панель Django
    path('admin/', admin.site.urls),

    # Все API-эндпоинты проекта (регистрация, каталог, корзина, заказы, импорт/экспорт)
    path('api/v1/', include('backend.urls', namespace='backend')),
]