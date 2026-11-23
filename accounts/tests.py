from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterViewTests(TestCase):
    def test_register_creates_user_wallet_and_logs_in(self):
        resp = self.client.post(reverse("register"), {
            "username": "newbie",
            "password": "secret123",
            "password_confirm": "secret123",
        })
        self.assertRedirects(resp, reverse("index"))

        user = User.objects.get(username="newbie")
        # кошелёк создан сигналом — ровно один, со стартовым капиталом
        self.assertEqual(user.wallet.balance, Decimal("10000"))

    def test_register_with_mismatched_passwords_fails(self):
        resp = self.client.post(reverse("register"), {
            "username": "newbie",
            "password": "secret123",
            "password_confirm": "secret124",
        })
        self.assertEqual(resp.status_code, 200)  # форма показана снова с ошибкой
        self.assertEqual(User.objects.count(), 0)
