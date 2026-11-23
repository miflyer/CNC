from django.core.management.base import BaseCommand

from market.models import Asset

# BNB нет на Kraken (запасном источнике), поэтому в списке ADA.
ASSETS = [
    {"ticker": "BTCUSDT", "symbol": "BTC", "name": "Bitcoin", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "ETHUSDT", "symbol": "ETH", "name": "Ethereum", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "SOLUSDT", "symbol": "SOL", "name": "Solana", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "ADAUSDT", "symbol": "ADA", "name": "Cardano", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "EURUSD", "symbol": "EUR", "name": "Евро / Доллар", "asset_type": Asset.AssetType.FOREX},
    {"ticker": "GBPUSD", "symbol": "GBP", "name": "Фунт / Доллар", "asset_type": Asset.AssetType.FOREX},
]


class Command(BaseCommand):
    help = "Создаёт стартовый набор активов и отключает те, что выпали из списка"

    def handle(self, *args, **options):
        # Активы, которых больше нет в списке (например BNB), выключаем —
        # без данных они только мешают
        actual_tickers = {item["ticker"] for item in ASSETS}
        for stale in Asset.objects.exclude(ticker__in=actual_tickers).filter(is_active=True):
            stale.is_active = False
            stale.save(update_fields=["is_active"])
            self.stdout.write(f"- {stale.symbol} отключён (нет данных ни у Binance, ни у Kraken)")

        for item in ASSETS:
            _, created = Asset.objects.get_or_create(ticker=item["ticker"], defaults=item)
            if created:
                self.stdout.write(self.style.SUCCESS(f"+ {item['symbol']} ({item['name']})"))
            else:
                self.stdout.write(f"= {item['symbol']} уже есть")
