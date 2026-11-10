from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class AccountsTests(TestCase):
    def test_profile_created_with_user(self):
        user = CustomUser.objects.create_user('neko', 'neko@example.com', 'pass12345')
        self.assertTrue(hasattr(user, 'profile'))

    def test_register_logs_in(self):
        resp = self.client.post(reverse('accounts:register'), {
            'username': 'cosplayer', 'email': 'c@example.com',
            'password1': 'Str0ng-pass!', 'password2': 'Str0ng-pass!',
        })
        self.assertRedirects(resp, reverse('shop:product_list'))
        self.assertTrue(CustomUser.objects.filter(username='cosplayer').exists())

    def test_profile_requires_login(self):
        resp = self.client.get(reverse('accounts:profile'))
        self.assertEqual(resp.status_code, 302)
