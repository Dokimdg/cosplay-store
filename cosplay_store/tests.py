from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from orders.invoice import build_invoice_pdf
from orders.models import Order, ShippingAddress
from shop.models import Category, Product


class SecurityTestBase(TestCase):
    def setUp(self):
        cache.clear()
        self.cat = Category.objects.create(name='Костюми', slug='kostyumy')
        self.p = Product.objects.create(category=self.cat, name='Плащ', slug='plashch', price=800, stock=5)


class CsrfTests(SecurityTestBase):
    def test_post_without_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        resp = client.post(reverse('cart:cart_add', args=[self.p.id]))
        self.assertEqual(resp.status_code, 403)

    def test_checkout_without_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('orders:checkout'), {}).status_code, 403)


class XssTests(SecurityTestBase):
    def test_product_name_is_escaped(self):
        Product.objects.create(category=self.cat, name='<script>alert(1)</script>', slug='xss', price=1, stock=1,
                               description='<img src=x onerror=alert(1)>')
        resp = self.client.get(reverse('shop:product_list'))
        self.assertNotContains(resp, '<script>alert(1)</script>')
        self.assertContains(resp, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_search_query_is_escaped(self):
        resp = self.client.get(reverse('shop:product_list'), {'q': '"><script>alert(1)</script>'})
        self.assertNotContains(resp, '<script>alert(1)</script>')

    def test_security_headers(self):
        resp = self.client.get(reverse('shop:product_list'))
        self.assertEqual(resp['X-Frame-Options'], 'DENY')
        self.assertEqual(resp['X-Content-Type-Options'], 'nosniff')
        csp = resp.get('Content-Security-Policy') or resp.get('Content-Security-Policy-Report-Only')
        self.assertIn("script-src 'self'", csp)

    def test_pdf_invoice_survives_markup_in_names(self):
        addr = ShippingAddress.objects.create(full_name='<b>Hack</b> & Co', phone='+380501234567',
                                              city='<i>Київ', address='<para>', postal_code='')
        order = Order.objects.create(shipping_address=addr)
        order.items.create(product=self.p, product_name='<font>Плащ</font> & <', price=1, quantity=1)
        self.assertTrue(build_invoice_pdf(order).startswith(b'%PDF'))


class SqlInjectionTests(SecurityTestBase):
    PAYLOADS = ["' OR '1'='1", "'; DROP TABLE shop_product; --", '" OR 1=1 --', "%' UNION SELECT 1,2,3 --"]

    def test_search_payloads_do_not_leak_or_break(self):
        for payload in self.PAYLOADS:
            resp = self.client.get(reverse('shop:product_list'), {'q': payload})
            self.assertEqual(resp.status_code, 200)
            self.assertNotContains(resp, 'Плащ')   # payload не зробив умову завжди істинною
        self.assertEqual(Product.objects.count(), 1)   # таблиця на місці

    def test_sort_is_whitelisted(self):
        resp = self.client.get(reverse('shop:product_list'), {'sort': 'price; DROP TABLE shop_product'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['sort'], '')

    def test_category_slug_payload_is_404(self):
        self.assertEqual(self.client.get("/kostyumy'%20OR%201=1/").status_code, 404)


class AuthSafetyTests(SecurityTestBase):
    def test_login_does_not_redirect_to_external_site(self):
        CustomUser.objects.create_user('neko', 'n@example.com', 'Str0ng-pass-123')
        resp = self.client.post(reverse('accounts:login') + '?next=https://evil.example/',
                                {'username': 'neko', 'password': 'Str0ng-pass-123'})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(resp['Location'].startswith('http'))


@override_settings(RATE_LIMIT_ENABLED=True)
class RateLimitTests(SecurityTestBase):
    def test_login_is_limited(self):
        url = reverse('accounts:login')
        for _ in range(10):
            self.assertNotEqual(self.client.post(url, {'username': 'x', 'password': 'y'}).status_code, 429)
        resp = self.client.post(url, {'username': 'x', 'password': 'y'})
        self.assertEqual(resp.status_code, 429)
        self.assertIn('Retry-After', resp)

    @override_settings(RATE_LIMIT_GLOBAL=(3, 60))
    def test_global_limit(self):
        url = reverse('shop:product_list')
        codes = [self.client.get(url).status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])

    def test_limit_is_per_ip(self):
        url = reverse('accounts:login')
        for _ in range(11):
            self.client.post(url, {'username': 'x', 'password': 'y'}, REMOTE_ADDR='10.0.0.1')
        other = self.client.post(url, {'username': 'x', 'password': 'y'}, REMOTE_ADDR='10.0.0.2')
        self.assertNotEqual(other.status_code, 429)

    @override_settings(NUM_PROXIES=0)
    def test_forwarded_header_ignored_without_trusted_proxy(self):
        url = reverse('accounts:login')
        for i in range(11):
            resp = self.client.post(url, {'username': 'x', 'password': 'y'}, HTTP_X_FORWARDED_FOR=f'1.2.3.{i}')
        self.assertEqual(resp.status_code, 429)   # підробка X-Forwarded-For не обходить ліміт
