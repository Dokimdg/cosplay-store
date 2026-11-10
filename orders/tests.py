from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from shop.models import Category, Product

from .models import Order

VALID = {'full_name': 'Іван Косплеєр', 'phone': '+380501234567', 'city': 'Київ',
         'address': 'Відділення №5', 'postal_code': '01001', 'comment': ''}


class OrderTestBase(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Костюми', slug='kostyumy')
        self.p = Product.objects.create(category=cat, name='Плащ', slug='plashch', price=800, stock=3)

    def make_order(self, qty=2):
        for _ in range(qty):
            self.client.post(reverse('cart:cart_add', args=[self.p.id]))
        self.client.post(reverse('orders:checkout'), VALID)
        return Order.objects.get()


class CheckoutTests(OrderTestBase):
    def test_empty_cart_redirects(self):
        self.assertRedirects(self.client.get(reverse('orders:checkout')), reverse('cart:cart_detail'))

    def test_successful_checkout(self):
        order = self.make_order(2)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(str(order.get_total_cost()), '1600.00')
        self.assertIsNotNone(order.estimated_delivery_date)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 1)
        resp = self.client.get(reverse('orders:order_detail', args=[order.id]))
        self.assertContains(resp, 'Орієнтовна дата доставки')
        self.assertContains(resp, 'Скасувати замовлення')

    def test_invalid_form_creates_nothing(self):
        self.client.post(reverse('cart:cart_add', args=[self.p.id]))
        resp = self.client.post(reverse('orders:checkout'), {**VALID, 'phone': '12'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_detail_hidden_from_strangers(self):
        order = self.make_order(1)
        self.assertEqual(self.client_class().get(reverse('orders:order_detail', args=[order.id])).status_code, 302)


class CancelTests(OrderTestBase):
    def test_cancel_within_24h_restores_stock(self):
        order = self.make_order(2)
        self.client.post(reverse('orders:order_cancel', args=[order.id]))
        order.refresh_from_db(); self.p.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.p.stock, 3)

    def test_cannot_cancel_after_24h(self):
        order = self.make_order(1)
        Order.objects.filter(pk=order.pk).update(created=timezone.now() - timedelta(hours=25))
        self.client.post(reverse('orders:order_cancel', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_cannot_cancel_shipped(self):
        order = self.make_order(1)
        Order.objects.filter(pk=order.pk).update(status=Order.Status.SHIPPED)
        self.client.post(reverse('orders:order_cancel', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_cancel_requires_post(self):
        order = self.make_order(1)
        self.assertEqual(self.client.get(reverse('orders:order_cancel', args=[order.id])).status_code, 405)

    def test_timeline_states(self):
        order = self.make_order(1)
        self.assertEqual([s['state'] for s in order.timeline], ['current', 'todo', 'todo', 'todo'])
        order.status = Order.Status.DELIVERED
        self.assertEqual([s['state'] for s in order.timeline], ['done'] * 4)
        order.status = Order.Status.CANCELLED
        self.assertEqual(order.timeline, [])


class InvoiceTests(OrderTestBase):
    def test_invoice_pdf(self):
        order = self.make_order(2)
        resp = self.client.get(reverse('orders:order_invoice', args=[order.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertContains(self.client.get(reverse('orders:order_detail', args=[order.id])), 'Завантажити рахунок')

    def test_invoice_not_for_strangers_or_cancelled(self):
        order = self.make_order(1)
        self.assertEqual(self.client_class().get(reverse('orders:order_invoice', args=[order.id])).status_code, 302)
        self.client.post(reverse('orders:order_cancel', args=[order.id]))
        self.assertEqual(self.client.get(reverse('orders:order_invoice', args=[order.id])).status_code, 302)
