from django.contrib import admin

from .models import Order, OrderItem, ShippingAddress


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ('product',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'shipping_address', 'status', 'estimated_delivery_date', 'created']
    list_filter = ['status', 'created']
    list_editable = ['status']
    inlines = [OrderItemInline]


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'city', 'address']
    search_fields = ['full_name', 'phone', 'city']
