from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from market.models import Asset
from trading.models import Order, Position, Trade
from trading.services import (
    cancel_order,
    execute_market_order,
    place_limit_order,
    process_pending_limit_orders,
)

# Примечание про параллельность: защита от двойной траты здесь —
# select_for_update() + transaction.atomic() в services.py. SQLite не эмулирует
# параллельные транзакции честно, поэтому многопоточный тест был бы нестабильным;
# корректность локов проверяется на PostgreSQL в проде. Здесь проверяем логику.


class TradingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="trader", password="pass12345")
        # кошелёк создаётся автоматически — см. accounts/signals.py
        self.wallet = self.user.wallet
        self.asset = Asset.objects.create(
            ticker="TESTUSDT", symbol="TEST", name="Test Coin",
            asset_type=Asset.AssetType.CRYPTO, current_price=Decimal("100"),
        )

    def test_buy_reduces_wallet_and_creates_position(self):
        execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("9000.00"))  # 10 шт. по 100$

        position = Position.objects.get(user=self.user, asset=self.asset)
        self.assertEqual(position.quantity, Decimal("10.00000000"))
        self.assertEqual(position.avg_price, Decimal("100"))

        self.assertEqual(Trade.objects.count(), 1)
        self.assertEqual(Order.objects.get().status, Order.Status.EXECUTED)

    def test_buy_with_insufficient_funds_rejected(self):
        with self.assertRaises(ValidationError):
            execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("200"))
        # деньги не тронуты
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("10000.00"))
        self.assertEqual(Trade.objects.count(), 0)

    def test_sell_without_position_rejected(self):
        with self.assertRaises(ValidationError):
            execute_market_order(self.user, self.asset.pk, Order.Side.SELL, Decimal("1"))

    def test_avg_price_is_weighted(self):
        execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"))
        self.asset.current_price = Decimal("200")
        self.asset.save()
        execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"))

        position = Position.objects.get(user=self.user, asset=self.asset)
        self.assertEqual(position.avg_price, Decimal("150"))  # (10*100 + 10*200) / 20

    def test_sell_all_zeroes_position(self):
        execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("5"))
        execute_market_order(self.user, self.asset.pk, Order.Side.SELL, Decimal("5"))

        position = Position.objects.get(user=self.user, asset=self.asset)
        self.assertEqual(position.quantity, Decimal("0"))
        self.assertEqual(position.avg_price, Decimal("0"))

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("10000.00"))

    def test_cannot_sell_more_than_available(self):
        execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("5"))
        with self.assertRaises(ValidationError):
            execute_market_order(self.user, self.asset.pk, Order.Side.SELL, Decimal("6"))

    def test_limit_buy_reserves_funds(self):
        place_limit_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"), Decimal("90"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("9100.00"))  # зарезервировано 900

    def test_limit_buy_executes_when_price_crosses(self):
        order = place_limit_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"), Decimal("90"))

        # цена выше лимита — не исполняется
        process_pending_limit_orders()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

        # цена упала до лимита — исполняется
        self.asset.current_price = Decimal("89")
        self.asset.save()
        executed = process_pending_limit_orders()
        self.assertEqual(executed, 1)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.EXECUTED)

        position = Position.objects.get(user=self.user, asset=self.asset)
        self.assertEqual(position.quantity, Decimal("10"))
        self.assertEqual(position.avg_price, Decimal("90"))

        # резерв превратился в актив — деньги не возвращаются
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("9100.00"))

    def test_cancel_limit_buy_returns_reserve(self):
        order = place_limit_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"), Decimal("90"))
        cancel_order(self.user, order.pk)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("10000.00"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_limit_sell_reserves_asset_then_executes(self):
        execute_market_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"))
        order = place_limit_order(self.user, self.asset.pk, Order.Side.SELL, Decimal("5"), Decimal("120"))

        # актив зарезервирован: доступно 5 из 10
        position = Position.objects.get(user=self.user, asset=self.asset)
        self.assertEqual(position.quantity, Decimal("5"))

        self.asset.current_price = Decimal("121")
        self.asset.save()
        process_pending_limit_orders()

        self.wallet.refresh_from_db()
        # потратили 1000 на покупку, получили 5*120 = 600 с продажи
        self.assertEqual(self.wallet.balance, Decimal("9600.00"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.EXECUTED)

    def test_cannot_cancel_executed_order(self):
        order = place_limit_order(self.user, self.asset.pk, Order.Side.BUY, Decimal("10"), Decimal("90"))
        cancel_order(self.user, order.pk)
        with self.assertRaises(ValidationError):
            cancel_order(self.user, order.pk)


class TradeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="trader", password="pass12345")
        self.asset = Asset.objects.create(
            ticker="TESTUSDT", symbol="TEST", name="Test Coin",
            asset_type=Asset.AssetType.CRYPTO, current_price=Decimal("100"),
        )

    def test_guest_cannot_trade(self):
        resp = self.client.post("/trade/", {
            "asset": self.asset.pk, "side": "buy",
            "order_type": "market", "quantity": "1",
        })
        self.assertEqual(resp.status_code, 302)  # редирект на страницу входа

    def test_market_buy_via_http(self):
        self.client.force_login(self.user)
        resp = self.client.post("/trade/", {
            "asset": self.asset.pk, "side": "buy", "order_type": "market",
            "quantity": "2", "asset_symbol": "TEST",
        })
        self.assertRedirects(resp, "/asset/TEST/")
        self.user.wallet.refresh_from_db()  # объект закэширован на момент создания
        self.assertEqual(self.user.wallet.balance, Decimal("9800.00"))

    def test_invalid_order_shows_error(self):
        self.client.force_login(self.user)
        resp = self.client.post("/trade/", {
            "asset": self.asset.pk, "side": "buy", "order_type": "market",
            "quantity": "999", "asset_symbol": "TEST",
        }, follow=True)
        self.assertContains(resp, "Недостаточно средств")
        self.assertEqual(self.user.wallet.balance, Decimal("10000.00"))
