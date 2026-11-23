from django.conf import settings
from django.db import models


class Order(models.Model):
    class Side(models.TextChoices):
        BUY = "buy", "Покупка"
        SELL = "sell", "Продажа"

    class Type(models.TextChoices):
        MARKET = "market", "Рыночная"
        LIMIT = "limit", "Лимитная"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        EXECUTED = "executed", "Исполнена"
        CANCELLED = "cancelled", "Отменена"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE)
    asset = models.ForeignKey("market.Asset", related_name="orders", on_delete=models.CASCADE)
    side = models.CharField(max_length=4, choices=Side.choices)
    order_type = models.CharField(max_length=6, choices=Type.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_side_display()} {self.quantity} {self.asset.symbol} ({self.get_status_display()})"


class Trade(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="trades", on_delete=models.CASCADE)
    asset = models.ForeignKey("market.Asset", related_name="trades", on_delete=models.CASCADE)
    side = models.CharField(max_length=4, choices=Order.Side.choices)
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)  # цена исполнения
    total = models.DecimalField(max_digits=20, decimal_places=2)  # сумма сделки в $
    order = models.ForeignKey(Order, related_name="trades", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_side_display()} {self.quantity} {self.asset.symbol} @ {self.price}"


class Position(models.Model):
    """Открытая позиция пользователя по активу."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="positions", on_delete=models.CASCADE)
    asset = models.ForeignKey("market.Asset", related_name="positions", on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=0)  # доступное количество (не в заявках)
    avg_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)  # средняя цена входа

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "asset"], name="unique_position"),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.quantity} {self.asset.symbol}"
