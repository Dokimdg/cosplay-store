from decimal import Decimal

from django.conf import settings

from shop.models import Product


class Cart:
    """Кошик, що зберігається в сесії Django (лише прості типи: str/int)."""

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if cart is None:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}

        if override_quantity:
            new_quantity = quantity
        else:
            new_quantity = self.cart[product_id]['quantity'] + quantity

        # Не дозволяємо замовити більше, ніж є на складі
        self.cart[product_id]['quantity'] = max(1, min(new_quantity, product.stock))
        self.cart[product_id]['price'] = str(product.price)
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        products = Product.objects.filter(id__in=self.cart.keys())
        products_by_id = {str(p.id): p for p in products}

        # Товари, яких більше немає в базі, прибираємо з кошика
        stale = [pid for pid in self.cart if pid not in products_by_id]
        for pid in stale:
            del self.cart[pid]
        if stale:
            self.save()

        # Віддаємо КОПІЇ, щоб не класти об'єкт Product у сесію (він не серіалізується в JSON)
        for pid, data in self.cart.items():
            price = Decimal(data['price'])
            yield {
                'product': products_by_id[pid],
                'quantity': data['quantity'],
                'price': price,
                'total_price': price * data['quantity'],
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(
            (Decimal(item['price']) * item['quantity'] for item in self.cart.values()),
            Decimal('0'),
        )

    def clear(self):
        self.session.pop(settings.CART_SESSION_ID, None)
        self.save()
