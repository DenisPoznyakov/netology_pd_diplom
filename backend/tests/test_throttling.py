from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from backend.models import User  # Импорт модели для создания пользователя напрямую


class ThrottlingTestCase(APITestCase):
    """
    Тесты для проверки работы ограничения частоты запросов (throttling)
    в Django REST Framework.

    Настроено в settings.py:
    - ScopedRateThrottle включён
    - scope 'login' = '5/m' (для тестов) или '20/h' (в продакшене)
    - Применяется к эндпоинтам регистрации и логина

    Тесты проверяют, что после 5 запросов возвращается 429 Too Many Requests.
    """

    def setUp(self):
        """
        Очищаем кэш перед каждым тестом, чтобы счётчик throttling начинался с нуля.
        """
        cache.clear()

    def test_registration_throttling(self):
        """
        Тест ограничения на регистрацию (RegisterAccount).
        Делает 10 запросов на /api/v1/user/register.
        Ожидается: первые 5 — успешные (200/400), с 6-го — 429.
        """
        url = reverse('backend:user-register')

        for i in range(10):
            data = {
                "email": f"reg_throttle_{i}@example.com",
                "password": "verystrongpass123",
                "first_name": "Reg",
                "last_name": "Throttle",
                "company": "Test Corp",
                "position": "Tester",
                "type": "buyer"
            }
            response = self.client.post(url, data, format='json')

            if i < 5:
                # 400 может быть из-за валидации, но не 429
                self.assertIn(response.status_code, [200, 400])
            else:
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
                self.assertIn('throttled', str(response.data).lower())
                return  # Тест прошёл — throttling сработал

        self.fail("Throttling не сработал на эндпоинте регистрации")

    def test_login_throttling(self):
        """
        Тест ограничения на логин (LoginAccount).
        Пользователь создаётся напрямую через модель (не через API),
        чтобы не тратить лимит 'login' на регистрацию.
        Ожидается: первые 5 логинов — 200 OK, с 6-го — 429.
        """
        # Создаём пользователя напрямую — без использования эндпоинта регистрации
        user = User.objects.create_user(
            email="login_throttle_test@example.com",
            password="verystrongpass123",
            first_name="Login",
            last_name="Throttle",
            type="buyer",
            is_active=True
        )
        user.save()

        login_url = reverse('backend:user-login')
        login_data = {
            "email": "login_throttle_test@example.com",
            "password": "verystrongpass123"
        }

        for i in range(10):
            response = self.client.post(login_url, login_data, format='json')

            if i < 5:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
                self.assertIn('throttled', str(response.data).lower())
                return  # Тест прошёл

        self.fail("Throttling не сработал на эндпоинте логина")