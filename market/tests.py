from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from market import services
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


class KrakenFallbackTests(TestCase):
    """Запасной источник крипты: разбор ответов Kraken при мёртвом Binance.

    Сеть мокаем: подменяем requests.get, чтобы тесты не зависели
    от интернета и не долбили чужие API.
    """

    KRAKEN_TICKER = {
        "error": [],
        "result": {
            "XXBTZUSD": {"c": ["50000.0", "1"], "o": "49000.0"},
        },
    }
    KRAKEN_OHLC = {
        "error": [],
        "result": {
            "XXBTZUSD": [
                [1700000000, "10", "12", "9", "11", "10.5", "100", 5],
                [1700003600, "11", "13", "10", "12", "11.5", "200", 7],
            ],
            "last": 1700003600,
        },
    }

    def setUp(self):
        self.btc = Asset.objects.create(
            ticker="BTCUSDT", symbol="BTC", name="Bitcoin",
            asset_type=Asset.AssetType.CRYPTO,
        )

    @patch("market.services.requests.get")
    def test_quotes_fall_back_to_kraken(self, mock_get):
        binance_resp = Mock()
        binance_resp.raise_for_status.side_effect = services.requests.HTTPError("451")
        kraken_resp = Mock()
        kraken_resp.json.return_value = self.KRAKEN_TICKER
        mock_get.side_effect = [binance_resp, kraken_resp]

        services.fetch_crypto_quotes([self.btc])

        self.btc.refresh_from_db()
        self.assertEqual(self.btc.current_price, Decimal("50000.0"))
        # изменение с открытия дня: (50000 - 49000) / 49000 * 100 = 2.04%
        self.assertEqual(self.btc.change_24h, Decimal("2.04"))

    @patch("market.services.requests.get")
    def test_candles_fall_back_to_kraken(self, mock_get):
        binance_resp = Mock()
        binance_resp.raise_for_status.side_effect = services.requests.HTTPError("451")
        kraken_resp = Mock()
        kraken_resp.json.return_value = self.KRAKEN_OHLC
        mock_get.side_effect = [binance_resp, kraken_resp]

        services.fetch_crypto_candles(self.btc, "1h")

        candles = list(self.btc.candles.filter(interval="1h").order_by("timestamp"))
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0].open, Decimal("10"))
        self.assertEqual(candles[1].close, Decimal("12"))
