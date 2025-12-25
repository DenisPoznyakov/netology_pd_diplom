import json
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from backend.models import User, Shop, Category, Product, ProductInfo, Order, OrderItem, Contact
from decimal import Decimal


class ShopAPITestCase(APITestCase):
    """
    Набор unit-тестов для проверки ключевых сценариев работы сервиса:
    - добавление товара в корзину покупателем,
    - оформление заказа из корзины,
    - изменение статуса заказа поставщиком.

    Тесты покрывают основной цикл взаимодействия покупателя и поставщика
    """

    def setUp(self):
        """
        Подготовка тестовых данных перед каждым тестом:
        - Создание пользователя-поставщика (тип 'shop') и магазина
        - Создание пользователя-покупателя (тип 'buyer')
        - Создание категории, продукта и предложения товара (ProductInfo)
        - Генерация токенов авторизации для обоих пользователей
        """
        # Поставщик
        self.shop_user = User.objects.create_user(
            username='shopuser',
            email='shop@example.com',
            password='testpass123',
            type='shop',
            is_active=True
        )
        self.shop = Shop.objects.create(name='Тестовый магазин', user=self.shop_user)
        self.shop_token = Token.objects.get_or_create(user=self.shop_user)[0]

        # Покупатель
        self.buyer = User.objects.create_user(
            username='buyeruser',
            email='buyer@example.com',
            password='testpass123',
            is_active=True
        )
        self.buyer_token = Token.objects.get_or_create(user=self.buyer)[0]

        # Категория
        self.category = Category.objects.create(name='Смартфоны')

        # Продукт
        self.product = Product.objects.create(name='iPhone Test', category=self.category)

        # ProductInfo — конкретное предложение товара в магазине
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=1001,
            price=Decimal('10000.00'),
            price_rrc=Decimal('12000.00'),
            quantity=10
        )

    def test_add_to_basket(self):
        """
        Тест добавления товара в корзину покупателем.
        Проверяет корректную авторизацию и успешный ответ API (/api/v1/basket).
        Формат запроса — через массив 'items' (поддержка нескольких товаров).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

        response = self.client.post('/api/v1/basket', {
            "items": [
                {
                    "product_info": self.product_info.id,
                    "quantity": 1
                }
            ]
        }, format='json')

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data.get('Status', False))

    def test_create_order(self):
        """
        Тест оформления заказа из корзины.
        Последовательно:
        1. Добавляет товар в корзину
        2. Создаёт контакт (адрес доставки)
        3. Находит корзину по статусу 'basket'
        4. Оформляет заказ через /api/v1/order
        Проверяет успешное создание заказа (Status: True).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

        # Добавляем в корзину через items
        response_add = self.client.post('/api/v1/basket', {
            "items": [
                {
                    "product_info": self.product_info.id,
                    "quantity": 1
                }
            ]
        }, format='json')
        add_data = json.loads(response_add.content)
        self.assertTrue(add_data.get('Status', False))

        # Создаём контакт
        contact = Contact.objects.create(
            user=self.buyer,
            city='Москва',
            street='Тестовая',
            house='1',
            phone='+79990000000'
        )

        # Находим корзину
        basket = Order.objects.filter(user=self.buyer, state='basket').first()
        self.assertIsNotNone(basket)

        # Оформляем заказ
        response = self.client.post('/api/v1/order', {
            "id": basket.id,
            "contact": contact.id
        }, format='json')

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data.get('Status', False))  # главное — Status True

    def test_partner_orders_status_change(self):
        """
        Тест изменения статуса заказа поставщиком.
        Создаёт заказ вручную (со статусом 'new'), затем поставщик меняет статус на 'confirmed'.
        Проверяет корректную авторизацию поставщика и успешное обновление.
        """
        # Создаём заказ вручную
        contact = Contact.objects.create(user=self.buyer, city='Москва', phone='+79990000000')
        order = Order.objects.create(user=self.buyer, state='new', contact=contact)
        OrderItem.objects.create(order=order, product_info=self.product_info, quantity=1)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.shop_token.key}')

        response = self.client.post('/api/v1/partner/orders', {
            "id": order.id,
            "status": "confirmed"
        }, format='json')

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response_data.get('Status', False))