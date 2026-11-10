from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ShopTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Перуки', slug='peruky')
        self.p = Product.objects.create(
            category=self.cat, name='Перука Рем', slug='peruka-rem',
            price=700, stock=3, description='Блакитна',
        )

    def test_list_and_category_and_search(self):
        self.assertContains(self.client.get(reverse('shop:product_list')), 'Перука Рем')
        self.assertContains(self.client.get(self.cat.get_absolute_url()), 'Перука Рем')
        self.assertNotContains(self.client.get(reverse('shop:product_list') + '?q=zzz'), 'Перука Рем')
        self.assertEqual(self.client.get(reverse('shop:product_list') + '?sort=price_asc&page=abc').status_code, 200)

    def test_detail(self):
        self.assertContains(self.client.get(self.p.get_absolute_url()), 'Екіпіруватися')
