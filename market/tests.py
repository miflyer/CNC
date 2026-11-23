from datetime import datetime, timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from market.models import Asset, Candle


class MarketPagesTests(TestCase):
    def setUp(self):
        self.asset = Asset.objects.create(
            ticker="TESTUSDT", symbol="TEST", name="Test Coin",
            asset_type=Asset.AssetType.CRYPTO,
            current_price=Decimal("100"), change_24h=Decimal("1.5"),
        )
        Candle.objects.create(
            asset=self.asset, interval="1d",
            timestamp=datetime(2026, 11, 1, tzinfo=timezone.utc),
            open=90, high=110, low=85, close=100,
        )

    def test_index_page(self):
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TEST")

    def test_asset_detail_page(self):
        resp = self.client.get(reverse("asset_detail", args=["TEST"]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Coin")

    def test_candles_json(self):
        resp = self.client.get(reverse("asset_candles", args=["TEST"]), {"interval": "1d"})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(len(payload["candles"]), 1)
        self.assertEqual(payload["candles"][0]["close"], 100.0)

    def test_prices_json(self):
        resp = self.client.get(reverse("prices"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["TEST"]["price"], "100")

    def test_leaderboard_page(self):
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(resp.status_code, 200)

    def test_portfolio_requires_login(self):
        resp = self.client.get(reverse("portfolio"))
        self.assertEqual(resp.status_code, 302)

    def test_portfolio_for_logged_in(self):
        user = User.objects.create_user(username="viewer", password="pass12345")
        self.client.force_login(user)
        resp = self.client.get(reverse("portfolio"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "10000")
