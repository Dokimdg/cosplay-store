from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Product


class CartTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Костюми', slug='kostyumy')
        self.p = Product.objects.create(category=cat, name='Плащ', slug='plashch', price=800, stock=2)

    def test_add_view_remove(self):
        self.client.post(reverse('cart:cart_add', args=[self.p.id]))
        self.client.post(reverse('cart:cart_add', args=[self.p.id]))
        self.client.post(reverse('cart:cart_add', args=[self.p.id]))  # понад склад
        resp = self.client.get(reverse('cart:cart_detail'))
        self.assertContains(resp, 'Плащ')
        self.assertEqual(len(resp.context['cart']), 2)
        self.client.post(reverse('cart:cart_remove', args=[self.p.id]))
        self.assertEqual(len(self.client.get(reverse('cart:cart_detail')).context['cart']), 0)

    def test_remove_requires_post(self):
        self.assertEqual(self.client.get(reverse('cart:cart_remove', args=[self.p.id])).status_code, 405)

    def test_deleted_product_does_not_break_cart(self):
        self.client.post(reverse('cart:cart_add', args=[self.p.id]))
        self.p.delete()
        self.assertEqual(self.client.get(reverse('cart:cart_detail')).status_code, 200)
