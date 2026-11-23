from django.db import models


class Asset(models.Model):
    class AssetType(models.TextChoices):
        CRYPTO = "crypto", "Криптовалюта"
        FOREX = "forex", "Валюта"

    ticker = models.CharField(max_length=20, unique=True)  # BTCUSDT — ключ для внешнего API
    symbol = models.CharField(max_length=10, unique=True)  # BTC — для URL и отображения
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices)
    is_active = models.BooleanField(default=True)

    # Котировки (обновляет команда update_prices)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    change_24h = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # в процентах
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.symbol} ({self.name})"


class Candle(models.Model):
    asset = models.ForeignKey(Asset, related_name="candles", on_delete=models.CASCADE)
    interval = models.CharField(max_length=5)  # 1h, 1d
    timestamp = models.DateTimeField()  # время открытия свечи, UTC
    open = models.DecimalField(max_digits=20, decimal_places=8)
    high = models.DecimalField(max_digits=20, decimal_places=8)
    low = models.DecimalField(max_digits=20, decimal_places=8)
    close = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.DecimalField(max_digits=30, decimal_places=8, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset", "interval", "timestamp"], name="unique_candle"),
        ]
        indexes = [models.Index(fields=["asset", "interval", "timestamp"])]
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.asset.symbol} {self.interval} {self.timestamp:%Y-%m-%d %H:%M}"
