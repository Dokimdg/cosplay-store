from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.cart import Cart
from cosplay_store.security import rate_limit
from shop.models import Product

from .forms import ShippingAddressForm
from .invoice import build_invoice_pdf
from .models import Order, OrderItem


def _initial_for(user):
    """Підставляємо дані профілю для авторизованого користувача"""
    if not user.is_authenticated:
        return {}
    profile = getattr(user, 'profile', None)
    return {
        'full_name': user.get_full_name(),
        'phone': getattr(profile, 'phone', ''),
        'address': getattr(profile, 'address', ''),
    }


@rate_limit('checkout', 10, 600)
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.info(request, 'Ваш кошик порожній.')
        return redirect('cart:cart_detail')

    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    order = _create_order(request, cart, form)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('cart:cart_detail')
            cart.clear()
            request.session['last_order_id'] = order.id
            messages.success(request, f'Дякуємо! Замовлення #{order.id} прийнято.')
            return redirect('orders:order_detail', order_id=order.id)
    else:
        form = ShippingAddressForm(initial=_initial_for(request.user))

    return render(request, 'orders/checkout.html', {'form': form})


def _create_order(request, cart, form):
    """Створює замовлення й списує залишки. Викликається всередині transaction.atomic()."""
    # Перечитуємо товари з бази з блокуванням, щоб перевірити актуальні залишки
    ids = [item['product'].id for item in cart]
    products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=ids, available=True)}

    items = []
    for item in cart:
        product = products.get(item['product'].id)
        if product is None:
            raise ValueError(f'«{item["product"].name}» більше недоступний. Оновіть кошик.')
        if item['quantity'] > product.stock:
            raise ValueError(f'«{product.name}»: на складі лише {product.stock} шт.')
        items.append((product, item['quantity']))

    address = form.save()
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        shipping_address=address,
    )
    for product, quantity in items:
        OrderItem.objects.create(
            order=order, product=product, product_name=product.name,
            price=product.price, quantity=quantity,
        )
        product.stock -= quantity
        product.save(update_fields=['stock', 'updated'])
    return order


def _get_own_order(request, order_id):
    """Замовлення доступне власнику або тому, хто оформив його в цій сесії (гість)"""
    order = get_object_or_404(
        Order.objects.select_related('shipping_address').prefetch_related('items'), id=order_id
    )
    is_owner = request.user.is_authenticated and order.user_id == request.user.id
    if not (is_owner or request.session.get('last_order_id') == order.id):
        return None
    return order


def order_detail(request, order_id):
    order = _get_own_order(request, order_id)
    if order is None:
        return redirect('shop:product_list')
    return render(request, 'orders/detail.html', {'order': order})


@login_required
def order_list(request):
    orders = request.user.orders.select_related('shipping_address')
    return render(request, 'orders/list.html', {'orders': orders})


@require_POST
@rate_limit('order_cancel', 10, 600)
def order_cancel(request, order_id):
    order = _get_own_order(request, order_id)
    if order is None:
        return redirect('shop:product_list')

    with transaction.atomic():
        # Перечитуємо замовлення під блокуванням, щоб уникнути подвійного скасування
        order = Order.objects.select_for_update().get(pk=order.pk)
        if not order.can_be_cancelled():
            messages.error(
                request,
                'Скасувати замовлення неможливо: його можна скасувати лише протягом 24 годин '
                'після створення і до відправлення.',
            )
            return redirect('orders:order_detail', order_id=order.id)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated'])
        # Повертаємо товари на склад
        for item in order.items.exclude(product=None):
            Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)

    messages.success(request, f'Замовлення #{order.id} скасовано.')
    return redirect('orders:order_detail', order_id=order.id)


@rate_limit('invoice', 30, 60, methods=('GET',))
def order_invoice(request, order_id):
    order = _get_own_order(request, order_id)
    if order is None:
        return redirect('shop:product_list')
    if order.status == Order.Status.CANCELLED:
        messages.error(request, 'Для скасованого замовлення рахунок недоступний.')
        return redirect('orders:order_detail', order_id=order.id)
    response = HttpResponse(build_invoice_pdf(order), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{order.id}.pdf"'
    return response
