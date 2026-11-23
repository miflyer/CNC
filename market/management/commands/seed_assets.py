from django.core.management.base import BaseCommand

from market.models import Asset

ASSETS = [
    {"ticker": "BTCUSDT", "symbol": "BTC", "name": "Bitcoin", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "ETHUSDT", "symbol": "ETH", "name": "Ethereum", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "BNBUSDT", "symbol": "BNB", "name": "BNB", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "SOLUSDT", "symbol": "SOL", "name": "Solana", "asset_type": Asset.AssetType.CRYPTO},
    {"ticker": "EURUSD", "symbol": "EUR", "name": "Евро / Доллар", "asset_type": Asset.AssetType.FOREX},
    {"ticker": "GBPUSD", "symbol": "GBP", "name": "Фунт / Доллар", "asset_type": Asset.AssetType.FOREX},
]


class Command(BaseCommand):
    help = "Создаёт стартовый набор активов биржи"

    def handle(self, *args, **options):
        for item in ASSETS:
            _, created = Asset.objects.get_or_create(ticker=item["ticker"], defaults=item)
            if created:
                self.stdout.write(self.style.SUCCESS(f"+ {item['symbol']} ({item['name']})"))
            else:
                self.stdout.write(f"= {item['symbol']} уже есть")
