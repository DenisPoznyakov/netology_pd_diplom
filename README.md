# Дипломный проект Netology: Backend интернет-магазина для автоматизации закупок

## Краткое описание проекта

Backend-сервис на **Django REST Framework** для розничной сети, реализующий полный цикл закупок:

* **Покупатели**: регистрация, авторизация (Token), восстановление пароля, просмотр каталога, добавление товаров в корзину, оформление заказа с выбором адреса доставки, просмотр истории заказов.
* **Поставщики (магазины)**: импорт товаров из YAML-прайса, экспорт текущего ассортимента в YAML, включение/отключение приёма заказов, просмотр оформленных заказов (только свои товары), изменение статуса заказа (confirmed → assembled → sent).
* Дополнительно реализованы: unit-тесты (покрывают добавление в корзину, оформление заказа и смену статуса), отправка уведомлений на email (в консоль в режиме разработки), характеристика товаров через параметры.

---

## Технологии

* Django 5.2
* Django REST Framework
* PyYAML
* django-rest-passwordreset
* python-social-auth
* SQLite (по умолчанию)
* Celery + Redis (асинхронная обработка задач)

---

## Инструкция по запуску

### 1. Клонирование репозитория

```bash
git clone https://github.com/DenisPoznyakov/netology_pd_diplom.git
cd netology_pd_diplom
```

### 2. Создание и активация виртуального окружения

**Windows:**

```bash
python -m venv env
env\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv env
source env/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Применение миграций

```bash
python manage.py migrate
```

### 5. (Опционально) Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 6. Запуск сервера разработки

```bash
python manage.py runserver
```

Сервис будет доступен по адресу: [http://127.0.0.1:8000](http://127.0.0.1:8000)
Админка: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

## Основные API эндпоинты

Все эндпоинты начинаются с `/api/v1/`.
Авторизация через заголовок `Authorization: Token <токен>`.

### Общие

* `POST /user/register` — регистрация пользователя
* `POST /user/register/confirm` — подтверждение email
* `POST /user/login` — получение токена
* `POST /user/password_reset` — запрос сброса пароля
* `POST /user/password_reset/confirm` — подтверждение нового пароля
* `GET /user/details` — данные текущего пользователя

### Покупатель

* `GET /categories` — список категорий
* `GET /shops` — список магазинов
* `GET /products` — каталог товаров (с фильтрами)
* `POST /basket` — добавить товары в корзину
  Формат:

  ```json
  {"items": [{"product_info": "id", "quantity": "n"}]}
  ```
* `GET /basket` — просмотр корзины
* `DELETE /basket` — удаление товаров из корзины
* `GET /user/contact`, `POST /user/contact`, `PUT /user/contact`, `DELETE /user/contact` — управление адресами доставки
* `POST /order` — оформление заказа из корзины
  Тело:

  ```json
  {"id": "<id_корзины>", "contact": "<id_контакта>"}
  ```
* `GET /orders` — список заказов покупателя

### Поставщик (type='shop')

* `POST /partner/update` — импорт прайса из YAML
  Тело: `{"url": "ссылка_на_yaml"}` или файл
* `GET /partner/state` / `POST /partner/state` — статус приёма заказов
* `GET /partner/orders` — список оформленных заказов (только свои товары)
* `POST /partner/orders` — изменение статуса заказа
  Тело: `{"id": "<id_заказа>", "status": "confirmed|assembled|sent"}`
* `GET /partner/export` — экспорт текущего ассортимента в YAML (скачивается файл)

---

## Тестирование

Проект содержит unit-тесты, покрывающие ключевые сценарии:

* Добавление товара в корзину
* Оформление заказа
* Изменение статуса заказа поставщиком
* Ограничение частоты запросов (Throttling)

Запуск тестов:

```bash
python manage.py test backend
```

---

## Асинхронные задачи (Celery)

- Отправка email (подтверждение регистрации, сброс пароля, уведомления о заказе) переведена на асинхронные задачи Celery.
- Брокер — Redis (localhost:6379).
- Задача: `backend.tasks.send_email_task`.
- Запуск:
  - Redis: `redis-server.exe`
  - Celery: `python -m celery -A netology_pd_diplom worker -l info`
  - Django: `python manage.py runserver`

При регистрации пользователя через API в консоли Celery видно выполнение задачи send_email_task.

## Документация API

Автоматическая документация доступна по адресам:

- Swagger UI (интерактивный): http://127.0.0.1:8000/swagger/
- Redoc (красивый вид): http://127.0.0.1:8000/redoc/

Генерируется с помощью DRF-Spectacular на основе кода и docstring.

## Ограничение частоты запросов (Throttling)
- Настроено в REST_FRAMEWORK:
  - Анонимные пользователи: 60 запросов/час
  - Авторизованные: 300 запросов/час
  - Регистрация и логин: 20 запросов/час (scope 'login')
  - Сброс пароля: 10 запросов/день

## Автор

Позняков Денис Андреевич

Дипломный проект профессии «Python-разработчик: расширенный курс»

Netology, 2025
