from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import Wallet
from market.models import Asset

from .models import Order, Position, Trade

QTY_QUANT = Decimal("0.00000001")  # точность количества (как у Binance)
MONEY_QUANT = Decimal("0.01")  # точность денег


def to_money(value):
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def get_position_locked(user, asset):
    """Позиция с блокировкой строки (select_for_update) внутри транзакции."""
    position, _ = Position.objects.select_for_update().get_or_create(
        user=user, asset=asset, defaults={"quantity": 0, "avg_price": 0}
    )
    return position


def validate_quantity(quantity):
    qty = quantity.quantize(QTY_QUANT)
    if qty <= 0:
        raise ValidationError("Количество должно быть больше нуля")
    return qty


@transaction.atomic
def execute_market_order(user, asset_id, side, quantity):
    """Рыночная заявка: покупка/продажа по текущей цене актива.

    Критично: всё внутри transaction.atomic, кошелёк и позиция
    блокируются select_for_update — два одновременных запроса
    не смогут потратить одни и те же деньги дважды.
    """
    asset = Asset.objects.select_for_update().get(pk=asset_id, is_active=True)
    if asset.current_price is None:
        raise ValidationError("Нет актуальной цены по этому активу")

    qty = validate_quantity(quantity)
    price = asset.current_price
    wallet = Wallet.objects.select_for_update().get(user=user)

    if side == Order.Side.BUY:
        total = to_money(qty * price)
        if wallet.balance < total:
            raise ValidationError(f"Недостаточно средств: нужно {total}$, на балансе {wallet.balance}$")
        wallet.balance -= total
        wallet.save(update_fields=["balance"])

        position = get_position_locked(user, asset)
        new_qty = position.quantity + qty
        position.avg_price = (
            position.avg_price * position.quantity + price * qty
        ) / new_qty
        position.quantity = new_qty
        position.save(update_fields=["quantity", "avg_price"])
    else:
        try:
            position = Position.objects.select_for_update().get(user=user, asset=asset)
        except Position.DoesNotExist:
            raise ValidationError("Нет позиции по этому активу")
        if position.quantity < qty:
            raise ValidationError(f"Недостаточно актива: есть {position.quantity}, нужно {qty}")
        total = to_money(qty * price)
        position.quantity -= qty
        if position.quantity == 0:
            position.avg_price = Decimal(0)
        position.save(update_fields=["quantity", "avg_price"])

        wallet.balance += total
        wallet.save(update_fields=["balance"])

    order = Order.objects.create(
        user=user, asset=asset, side=side, order_type=Order.Type.MARKET,
        status=Order.Status.EXECUTED, quantity=qty, price=price,
        executed_at=timezone.now(),
    )
    Trade.objects.create(user=user, asset=asset, side=side, quantity=qty, price=price, total=total, order=order)
    return order


@transaction.atomic
def place_limit_order(user, asset_id, side, quantity, limit_price):
    """Лимитная заявка. При размещении РЕЗЕРВИРУЕМ средства или актив,
    чтобы они не были потрачены дважды до исполнения."""
    asset = Asset.objects.get(pk=asset_id, is_active=True)
    qty = validate_quantity(quantity)
    price = limit_price.quantize(MONEY_QUANT)
    if price <= 0:
        raise ValidationError("Цена заявки должна быть больше нуля")

    if side == Order.Side.BUY:
        wallet = Wallet.objects.select_for_update().get(user=user)
        reserve = to_money(qty * price)
        if wallet.balance < reserve:
            raise ValidationError(f"Недостаточно средств для резерва: нужно {reserve}$")
        wallet.balance -= reserve
        wallet.save(update_fields=["balance"])
    else:
        position = get_position_locked(user, asset)
        if position.quantity < qty:
            raise ValidationError(f"Недостаточно актива: есть {position.quantity}, нужно {qty}")
        position.quantity -= qty  # резервируем актив, убрав его из доступного
        position.save(update_fields=["quantity"])

    return Order.objects.create(
        user=user, asset=asset, side=side, order_type=Order.Type.LIMIT,
        status=Order.Status.PENDING, quantity=qty, price=price,
    )


@transaction.atomic
def cancel_order(user, order_id):
    order = Order.objects.select_for_update().select_related("asset").get(pk=order_id, user=user)
    if order.status != Order.Status.PENDING:
        raise ValidationError("Заявку уже нельзя отменить")
    if order.side == Order.Side.BUY:
        wallet = Wallet.objects.select_for_update().get(user=user)
        wallet.balance += to_money(order.quantity * order.price)
        wallet.save(update_fields=["balance"])
    else:
        position = get_position_locked(user, order.asset)
        position.quantity += order.quantity  # возвращаем зарезервированный актив
        position.save(update_fields=["quantity"])
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def execute_limit_order(order):
    """Исполнение лимитной заявки по её цене. Вызывается из update_prices."""
    order = Order.objects.select_for_update().select_related("asset").get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        return None
    qty, price = order.quantity, order.price
    user, asset = order.user, order.asset

    if order.side == Order.Side.BUY:
        # Средства уже зарезервированы при размещении — списывать не нужно
        position = get_position_locked(user, asset)
        new_qty = position.quantity + qty
        position.avg_price = (position.avg_price * position.quantity + price * qty) / new_qty
        position.quantity = new_qty
        position.save(update_fields=["quantity", "avg_price"])
    else:
        # Актив уже зарезервирован при размещении
        wallet = Wallet.objects.select_for_update().get(user=user)
        wallet.balance += to_money(qty * price)
        wallet.save(update_fields=["balance"])

    total = to_money(qty * price)
    trade = Trade.objects.create(user=user, asset=asset, side=order.side, quantity=qty, price=price, total=total, order=order)
    order.status = Order.Status.EXECUTED
    order.executed_at = timezone.now()
    order.save(update_fields=["status", "executed_at"])
    return trade


def process_pending_limit_orders():
    """Проверяет все ожидающие заявки против текущих цен.
    BUY исполняется, когда цена <= лимита; SELL — когда цена >= лимита."""
    executed = 0
    orders = Order.objects.select_related("asset").filter(
        status=Order.Status.PENDING, asset__current_price__isnull=False
    )
    for order in orders:
        price = order.asset.current_price
        hit = (order.side == Order.Side.BUY and price <= order.price) or (
            order.side == Order.Side.SELL and price >= order.price
        )
        if not hit:
            continue
        try:
            with transaction.atomic():
                execute_limit_order(order)
            executed += 1
        except Exception:
            # Не смогли исполнить (например, сработала защита целостности) —
            # отменяем заявку, деньги/актив уже вернутся? нет: возвращаем вручную.
            with transaction.atomic():
                try:
                    cancel_order(order.user, order.pk)
                except Exception:
                    pass
    return executed
