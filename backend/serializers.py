from rest_framework import serializers
from backend.models import User, Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order, Contact


class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Contact (адреса доставки пользователя).
    Используется для создания, обновления и просмотра контактов покупателя.
    Поле user доступно только для записи (автоматически заполняется текущим пользователем).
    """
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели User.
    Возвращает основную информацию о пользователе и список его контактов (адресов доставки).
    Используется в эндпоинтах получения деталей пользователя.
    """
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Category.
    Возвращает идентификатор и название категории товаров.
    Используется при выводе каталога и фильтрации товаров.
    """
    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Shop.
    Возвращает информацию о магазине: название и статус приёма заказов.
    Используется в списке магазинов и при выводе товаров.
    """
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Product.
    Возвращает название продукта и строковое представление категории.
    Используется как вложенный сериализатор в ProductInfo.
    """
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели ProductParameter.
    Возвращает название параметра (например, "Цвет") и его значение.
    Реализует гибкую систему характеристик товаров.
    """
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели ProductInfo — основная информация о товаре в конкретном магазине.
    Включает вложенные данные о продукте и списке параметров (характеристик).
    Используется в каталоге товаров, корзине и заказе.
    """
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели OrderItem (позиция в заказе).
    Используется при создании и обновлении позиций заказа.
    Поле order доступно только для записи (связывается автоматически).
    """
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    """
    Расширенный сериализатор для OrderItem при создании заказа.
    Включает полную информацию о товаре (ProductInfo) для удобного отображения в ответе.
    """
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Order.
    Возвращает полную информацию о заказе: позиции, статус, дату, общую сумму и контакт доставки.
    Общая сумма рассчитывается через метод get_total_sum (использует свойство модели).
    """
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)
    
    def get_total_sum(self, obj):
        """
        Возвращает общую сумму заказа.
        Использует свойство total_sum модели Order.
        """
        return obj.total_sum