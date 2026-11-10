from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class ShippingAddress(models.Model):
    """Адреса доставки (окремий запис для кожного замовлення)"""
    full_name = models.CharField('Ім\'я та прізвище', max_length=150)
    phone = models.CharField('Телефон', max_length=20)
    city = models.CharField('Місто', max_length=100)
    address = models.CharField('Адреса / відділення', max_length=255)
    postal_code = models.CharField('Поштовий індекс', max_length=10, blank=True)
    comment = models.TextField('Коментар до доставки', blank=True)

    class Meta:
        verbose_name = 'Адреса доставки'
        verbose_name_plural = 'Адреси доставки'

    def __str__(self):
        return f'{self.full_name}, {self.city}, {self.address}'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Очікує підтвердження'
        PROCESSING = 'processing', 'Комплектується'
        SHIPPED = 'shipped', 'Відправлене'
        DELIVERED = 'delivered', 'Доставлене'
        CANCELLED = 'cancelled', 'Скасоване'

    # Порядок етапів для timeline (скасоване в нього не входить)
    FLOW = [Status.PENDING, Status.PROCESSING, Status.SHIPPED, Status.DELIVERED]
    # Скасувати можна лише поки замовлення ще не відправлене
    CANCELLABLE_STATUSES = (Status.PENDING, Status.PROCESSING)
    CANCEL_WINDOW = timedelta(hours=24)
    DELIVERY_DAYS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='orders', verbose_name='Користувач',
    )
    shipping_address = models.OneToOneField(
        ShippingAddress, on_delete=models.PROTECT, related_name='order', verbose_name='Адреса доставки',
    )
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.PENDING)
    estimated_delivery_date = models.DateField('Орієнтовна дата доставки', null=True, blank=True)
    created = models.DateTimeField('Створено', auto_now_add=True)
    updated = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'

    def __str__(self):
        return f'Замовлення #{self.pk}'

    def save(self, *args, **kwargs):
        if self.estimated_delivery_date is None:
            self.estimated_delivery_date = timezone.localdate() + timedelta(days=self.DELIVERY_DAYS)
        super().save(*args, **kwargs)

    def get_total_cost(self):
        return sum((item.get_cost() for item in self.items.all()), Decimal('0'))

    # --- скасування ---
    @property
    def cancel_deadline(self):
        return self.created + self.CANCEL_WINDOW

    def can_be_cancelled(self):
        return (
            self.status in self.CANCELLABLE_STATUSES
            and timezone.now() <= self.cancel_deadline
        )

    # --- timeline ---
    @property
    def timeline(self):
        """Етапи для візуалізації: state = done | current | todo"""
        if self.status == self.Status.CANCELLED:
            return []
        current = self.FLOW.index(self.status)
        steps = []
        for i, st in enumerate(self.FLOW):
            state = 'done' if i < current else 'current' if i == current else 'todo'
            if st == self.Status.DELIVERED and i == current:
                state = 'done'
            steps.append({'label': st.label, 'state': state})
        return steps


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Товар може бути видалений з каталогу, тому SET_NULL + знімок назви й ціни
    product = models.ForeignKey(
        'shop.Product', null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items',
    )
    product_name = models.CharField('Назва', max_length=200)
    price = models.DecimalField('Ціна', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Кількість', default=1)

    class Meta:
        verbose_name = 'Позиція замовлення'
        verbose_name_plural = 'Позиції замовлення'

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    def get_cost(self):
        return self.price * self.quantity
