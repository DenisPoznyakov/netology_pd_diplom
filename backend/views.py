import yaml
import json

from rest_framework.request import Request
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse, HttpResponse
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from yaml import load as load_yaml, Loader

from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, STATE_CHOICES
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer
from backend.signals import new_user_registered, new_order


def strtobool(value):
    """
    Преобразует строку в булево значение.
    Совместимо с distutils.util.strtobool, используется для обработки поля 'state' в PartnerState.
    """
    if isinstance(value, bool):
        return value
    value = str(value).lower()
    if value in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif value in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"Недопустимое значение для булева: {value}")


class RegisterAccount(APIView):
    """
    Эндпоинт для регистрации новых покупателей.
    Создаёт неактивного пользователя и отправляет письмо с токеном подтверждения email (через сигналы).
    """

    def post(self, request, *args, **kwargs):
        """
        Обработка POST-запроса на регистрацию.
        Проверяет наличие обязательных полей, валидирует пароль и сохраняет пользователя.
        """
        required_fields = {'first_name', 'last_name', 'email', 'password', 'company', 'position'}
        if not required_fields.issubset(request.data):
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

        try:
            validate_password(request.data['password'])
        except Exception as password_error:
            return JsonResponse({'Status': False, 'Errors': {'password': list(password_error)}})

        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            user.set_password(request.data['password'])
            user.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class ConfirmAccount(APIView):
    """
    Эндпоинт для подтверждения email после регистрации.
    Активирует пользователя и удаляет использованный токен.
    """

    def post(self, request, *args, **kwargs):
        """
        Обработка POST-запроса с email и токеном.
        Активирует пользователя при совпадении токена.
        """
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(
                user__email=request.data['email'],
                key=request.data['token']
            ).first()

            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView):
    """
    Эндпоинт для просмотра и редактирования данных авторизованного пользователя.
    GET — получение данных, POST — обновление (включая смену пароля).
    """

    def get(self, request: Request, *args, **kwargs):
        """
        Возвращает данные текущего авторизованного пользователя (с контактами).
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Обновляет данные пользователя, включая смену пароля (с валидацией).
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                return JsonResponse({'Status': False, 'Errors': {'password': list(password_error)}})
            else:
                request.user.set_password(request.data['password'])

        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Эндпоинт для авторизации пользователей.
    Возвращает токен аутентификации (TokenAuthentication).
    """

    def post(self, request, *args, **kwargs):
        """
        Аутентифицирует пользователя по email и паролю, выдаёт или возвращает существующий токен.
        """
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user and user.is_active:
                token, _ = Token.objects.get_or_create(user=user)
                return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class CategoryView(ListAPIView):
    """
    Эндпоинт для получения списка всех категорий товаров.
    Доступен всем пользователям.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Эндпоинт для получения списка активных магазинов (state=True).
    Доступен всем пользователям.
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
    Эндпоинт для поиска и фильтрации товаров в каталоге.
    Поддерживает фильтры по shop_id и category_id.
    Возвращает только товары из активных магазинов.
    """

    def get(self, request: Request, *args, **kwargs):
        """
        Фильтрует товары по магазину и/или категории, возвращает детальную информацию (с параметрами).
        """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query &= Q(shop_id=shop_id)
        if category_id:
            query &= Q(product__category_id=category_id)

        queryset = ProductInfo.objects.filter(query).select_related(
            'shop', 'product__category'
        ).prefetch_related(
            'product_parameters__parameter'
        ).distinct()

        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class BasketView(APIView):
    """
    Эндпоинт для работы с корзиной покупателя.
    GET — просмотр корзины,
    POST — добавление товаров (через массив items),
    PUT — обновление количества,
    DELETE — удаление товаров.
    Корзина реализуется как заказ со статусом 'basket'.
    """

    def get(self, request, *args, **kwargs):
        """
        Возвращает содержимое корзины текущего пользователя (заказ со статусом 'basket').
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        basket = Order.objects.filter(
            user_id=request.user.id, state='basket'
        ).prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter',
            'ordered_items__product_info'
        ).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Добавляет товары в корзину (поддержка нескольких позиций через 'items').
        Создаёт корзину автоматически, если её нет.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_list = request.data.get('items')
        if not items_list or not isinstance(items_list, list):
            return JsonResponse({'Status': False, 'Errors': 'Неверный формат: ожидается список "items"'})

        basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
        objects_created = 0

        for order_item_data in items_list:
            order_item_data = order_item_data.copy()
            order_item_data['order'] = basket.id
            serializer = OrderItemSerializer(data=order_item_data)
            if serializer.is_valid():
                try:
                    serializer.save()
                    objects_created += 1
                except IntegrityError as error:
                    return JsonResponse({'Status': False, 'Errors': str(error)})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': True, 'Создано объектов': objects_created})

    def delete(self, request, *args, **kwargs):
        """
        Удаляет все товары из корзины (или корзину целиком, если она пуста).
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        try:
            basket = Order.objects.get(user_id=request.user.id, state='basket')
            deleted_count = OrderItem.objects.filter(order=basket).delete()[0]
            return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        except Order.DoesNotExist:
            return JsonResponse({'Status': True, 'Удалено объектов': 0})

    def put(self, request, *args, **kwargs):
        """
        Обновляет количество товаров в корзине.
        Если quantity = 0 — удаляет позицию.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_list = request.data.get('items')
        if not items_list or not isinstance(items_list, list):
            return JsonResponse({'Status': False, 'Errors': 'Неверный формат: ожидается список "items"'})

        basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
        objects_updated = 0

        for item_data in items_list:
            product_info_id = item_data.get('product_info')
            quantity = item_data.get('quantity')
            if product_info_id is None or quantity is None:
                continue

            try:
                order_item = OrderItem.objects.get(order=basket, product_info_id=product_info_id)
            except OrderItem.DoesNotExist:
                continue

            if quantity > 0:
                order_item.quantity = quantity
                order_item.save()
                objects_updated += 1
            else:
                order_item.delete()
                objects_updated += 1

        return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})


class PartnerUpdate(APIView):
    """
    Эндпоинт для импорта/обновления прайс-листа поставщиком.
    Поддерживает загрузку YAML-файла через form-data или по URL.
    Удаляет старые товары магазина и загружает новые.
    """

    def post(self, request, *args, **kwargs):
        """
        Основная логика импорта товаров из YAML.
        Обрабатывает категории, продукты, цены и параметры.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        data = None

        if 'file' in request.FILES:
            yaml_file = request.FILES['file']
            try:
                stream = yaml_file.read()
                data = load_yaml(stream, Loader=Loader)
            except yaml.YAMLError as e:
                return JsonResponse({'Status': False, 'Errors': f'Неверный формат YAML: {str(e)}'})
            except Exception as e:
                return JsonResponse({'Status': False, 'Errors': f'Ошибка чтения файла: {str(e)}'})
        else:
            url = request.data.get('url')
            if not url:
                return JsonResponse({'Status': False, 'Errors': 'Необходимо загрузить файл или указать URL'})

            try:
                if url.startswith('file://'):
                    local_path = url[7:]
                    if local_path.startswith('/'):
                        local_path = local_path[1:]
                    with open(local_path, 'rb') as f:
                        stream = f.read()
                else:
                    response = get(url)
                    response.raise_for_status()
                    stream = response.content

                data = load_yaml(stream, Loader=Loader)
            except yaml.YAMLError as e:
                return JsonResponse({'Status': False, 'Errors': f'Неверный формат YAML: {str(e)}'})
            except FileNotFoundError:
                return JsonResponse({'Status': False, 'Errors': 'Локальный файл не найден'})
            except Exception as e:
                return JsonResponse({'Status': False, 'Errors': f'Ошибка загрузки по URL: {str(e)}'})

        if not isinstance(data, dict):
            return JsonResponse({'Status': False, 'Errors': 'Неверная структура YAML: ожидался объект верхнего уровня'})

        shop, _ = Shop.objects.get_or_create(
            user_id=request.user.id,
            defaults={'name': data.get('shop', 'Без названия')}
        )
        shop.name = data.get('shop', shop.name)
        shop.save()

        for category_data in data.get('categories', []):
            category_obj, _ = Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']}
            )
            category_obj.shops.add(shop)
            category_obj.save()

        ProductInfo.objects.filter(shop_id=shop.id).delete()

        for item in data.get('goods', []):
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category']
            )

            product_info = ProductInfo.objects.create(
                product_id=product.id,
                shop_id=shop.id,
                external_id=item['id'],
                model=item.get('model', ''),
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
            )

            for param_name, param_value in item.get('parameters', {}).items():
                parameter_obj, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_obj.id,
                    value=str(param_value)
                )

        return JsonResponse({'Status': True, 'Сообщение': 'Прайс-лист успешно загружен'})


class PartnerState(APIView):
    """
    Эндпоинт для управления статусом приёма заказов магазином.
    GET — получение текущего статуса, POST — изменение (true/false).
    """

    def get(self, request, *args, **kwargs):
        """
        Возвращает текущий статус приёма заказов магазина поставщика.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Изменяет статус приёма заказов (state) для магазина текущего поставщика.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        state = request.data.get('state')
        if state is not None:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    """
    Эндпоинт для работы поставщика с заказами.
    GET — просмотр оформленных заказов (только с товарами своего магазина),
    POST — изменение статуса заказа с уведомлением покупателя по email.
    """

    def get(self, request):
        """
        Возвращает список оформленных заказов, содержащих товары текущего магазина.
        Исключает корзины (state='basket').
        """
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        orders = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id
        ).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter',
            'ordered_items__product_info'
        ).select_related('contact').distinct()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Изменяет статус заказа (confirmed → assembled → sent).
        Отправляет уведомление покупателю на email при успешном изменении.
        """
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order_id = request.data.get('id')
        status = request.data.get('status')

        if not order_id or not status:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны id заказа или статус'})

        if status not in [choice[0] for choice in STATE_CHOICES]:
            return JsonResponse({'Status': False, 'Errors': 'Недопустимый статус'})

        try:
            order = Order.objects.filter(
                id=order_id,
                ordered_items__product_info__shop__user_id=request.user.id,
                state__in=['new', 'confirmed', 'assembled', 'sent']
            ).first()

            if not order:
                return JsonResponse({'Status': False, 'Errors': 'Заказ не найден или недоступен для изменения'}, status=403)

            order.state = status
            order.save()

            # Уведомление покупателю об изменении статуса
            subject = f'Статус вашего заказа #{order.id} изменён'
            message = f'Новый статус: {order.get_state_display()}\nДата: {order.dt}'
            send_mail(
                subject,
                message,
                'from@example.com',
                [order.user.email],
                fail_silently=False,
            )
            return JsonResponse({'Status': True, 'Сообщение': f'Статус заказа #{order_id} изменён на "{status}"'})

        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': str(e)})


class PartnerExport(APIView):
    """
    Продвинутый функционал: экспорт товаров магазина в YAML.
    Формат полностью совместим с импортом.
    Возвращает файл для скачивания.
    """

    def get(self, request):
        """
        Генерирует и возвращает YAML-файл с текущим ассортиментом магазина поставщика.
        """
        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        try:
            shop = Shop.objects.get(user_id=request.user.id)
        except Shop.DoesNotExist:
            return Response({'Status': False, 'Error': 'Магазин не найден'}, status=404)

        product_infos = ProductInfo.objects.filter(shop=shop).select_related(
            'product'
        ).prefetch_related('product_parameters__parameter').order_by('id')

        export_data = {
            'shop': shop.name,
            'products': []
        }

        for pi in product_infos:
            product_data = {
                'model': pi.external_id or pi.model,
                'name': pi.product.name,
                'price': str(pi.price),
                'price_rrc': str(pi.price_rrc),
                'quantity': pi.quantity,
                'parameters': {}
            }

            for param in pi.product_parameters.all():
                product_data['parameters'][param.parameter.name] = param.value

            export_data['products'].append(product_data)

        yaml_data = yaml.dump(export_data, allow_unicode=True, default_flow_style=False, sort_keys=False, indent=2)

        response = HttpResponse(yaml_data, content_type='text/yaml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="export_{shop.name.replace(" ", "_")}.yaml"'
        return response


class ContactView(APIView):
    """
    Эндпоинт для управления контактами (адресами доставки) покупателя.
    GET — список, POST — создание, PUT — обновление, DELETE — удаление.
    """

    def get(self, request, *args, **kwargs):
        """
        Возвращает список всех контактов текущего пользователя.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        contacts = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Создаёт новый контакт для текущего пользователя.
        Автоматически привязывает user_id.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        contact_data = request.data.copy()
        contact_data['user'] = request.user.id

        serializer = ContactSerializer(data=contact_data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors})

    def delete(self, request, *args, **kwargs):
        """
        Удаляет один или несколько контактов по списку ID.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            items_list = items_string.split(',')
            query = Q()
            for contact_id in items_list:
                if contact_id.isdigit():
                    query |= Q(user_id=request.user.id, id=contact_id)

            deleted_count = Contact.objects.filter(query).delete()[0]
            return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def put(self, request, *args, **kwargs):
        """
        Обновляет существующий контакт по ID.
        Доступно только для своих контактов.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data and request.data['id'].isdigit():
            contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
            if contact:
                serializer = ContactSerializer(contact, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrderView(APIView):
    """
    Эндпоинт для работы с заказами покупателя.
    GET — просмотр оформленных заказов,
    POST — оформление заказа из корзины (привязка контакта и смена статуса на 'new').
    """

    def get(self, request, *args, **kwargs):
        """
        Возвращает список оформленных заказов текущего пользователя (исключая корзину).
        Включает расчёт общей суммы через аннотацию.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        orders = Order.objects.filter(
            user_id=request.user.id
        ).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter'
        ).select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))
        ).distinct()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Оформляет заказ из корзины: привязывает контакт и меняет статус на 'new'.
        Вызывает сигнал new_order для отправки уведомления покупателю.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        order_id = request.data.get('id')
        contact_id = request.data.get('contact')

        if not order_id or not contact_id:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны id заказа или контакт'})

        try:
            order = Order.objects.get(user_id=request.user.id, id=order_id, state='basket')
        except Order.DoesNotExist:
            return JsonResponse({'Status': False, 'Errors': 'Заказ не найден или уже оформлен'})

        try:
            contact = Contact.objects.get(user_id=request.user.id, id=contact_id)
        except Contact.DoesNotExist:
            return JsonResponse({'Status': False, 'Errors': 'Контакт не найден'})

        order.contact = contact
        order.state = 'new'
        order.save()

        return JsonResponse({'Status': True, 'Сообщение': 'Заказ успешно оформлен'})