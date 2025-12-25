from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, ConfirmEmailToken

# -----------------------
# User
# -----------------------
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Административная панель для управления пользователями сервиса.
    Кастомизирована под модель User с дополнительными полями: company, position, type (shop/buyer).
    Позволяет удобно просматривать и редактировать пользователей разных типов (покупатели и поставщики).
    """
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position', 'type')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'company', 'position', 'type'),
        }),
    )

    list_display = ('email', 'first_name', 'last_name', 'company', 'position', 'type', 'is_staff')
    list_filter = ('type', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

# -----------------------
# Shop
# -----------------------
@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Shop (магазины поставщиков).
    Позволяет просматривать и редактировать информацию о магазинах, включая статус приёма заказов.
    """
    list_display = ('name', 'user', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'user__email')

# -----------------------
# Category
# -----------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Category (категории товаров).
    Отображает категории и связанные с ними магазины.
    """
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('shops',)

# -----------------------
# Product
# -----------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Product (продукты/наименования товаров).
    Позволяет управлять базовой информацией о товарах, категориями и отображает связанные магазины через ProductInfo.
    """
    list_display = ('name', 'category', 'get_shops')
    list_filter = ('category',)
    search_fields = ('name',)

    def get_shops(self, obj):
        """
        Возвращает список магазинов, где продаётся этот продукт
        через связанные ProductInfo.
        """
        shops = obj.product_infos.all().values_list('shop__name', flat=True)
        return ", ".join(shops)
    
    get_shops.short_description = 'Магазины'

# -----------------------
# ProductInfo
# -----------------------
@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ProductInfo (конкретные предложения товаров в магазинах).
    Отображает цены, количество, РРЦ и внешний идентификатор из прайса поставщика.
    """
    list_display = ('product', 'shop', 'external_id', 'price', 'price_rrc', 'quantity')
    list_filter = ('shop',)
    search_fields = ('product__name', 'external_id')

# -----------------------
# Parameter
# -----------------------
@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Parameter (названия характеристик товаров).
    Например: "Диагональ", "Объём памяти", "Цвет".
    """
    list_display = ('name',)
    search_fields = ('name',)

# -----------------------
# ProductParameter
# -----------------------
@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ProductParameter (значения характеристик для конкретных товаров).
    Реализует гибкую систему параметров товаров.
    """
    list_display = ('product_info', 'parameter', 'value')
    list_filter = ('parameter',)
    search_fields = ('value', 'parameter__name')

# -----------------------
# Order
# -----------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Order (заказы).
    Позволяет просматривать все заказы, их статусы, даты и связанные контакты.
    """
    list_display = ('id', 'user', 'dt', 'state', 'contact')
    list_filter = ('state', 'dt')
    search_fields = ('id', 'user__email')

# -----------------------
# OrderItem
# -----------------------
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderItem (позиции в заказе).
    Отображает товары, количество и магазин в каждом заказе.
    """
    list_display = ('order', 'product_info', 'quantity')
    list_filter = ('order__state',)
    search_fields = ('order__id', 'product_info__product__name')

# -----------------------
# Contact
# -----------------------
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Contact (адреса доставки пользователей).
    Позволяет управлять контактами покупателей.
    """
    list_display = ('user', 'city', 'street', 'phone')
    list_filter = ('city',)
    search_fields = ('user__email', 'phone')

# -----------------------
# ConfirmEmailToken
# -----------------------
@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """
    Административная панель для модели ConfirmEmailToken.
    Отображает токены подтверждения email при регистрации.
    """
    list_display = ('user', 'key', 'created_at')
    search_fields = ('user__email', 'key')
