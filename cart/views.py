from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cosplay_store.security import rate_limit
from shop.models import Product

from .cart import Cart


@require_POST
@rate_limit('cart_add', 60, 60)
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    if product.stock < 1:
        messages.error(request, f'«{product.name}» закінчився на складі.')
        return redirect(product.get_absolute_url())
    cart.add(product=product, quantity=1)
    messages.success(request, f'«{product.name}» додано до кошика.')
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')


def cart_detail(request):
    return render(request, 'cart/detail.html')
