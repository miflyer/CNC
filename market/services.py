"""Загрузка рыночных данных из внешних API.

Принцип: клиенты сайта НИКОГДА не ходят во внешние API напрямую.
Команда update_prices периодически забирает котировки и свечи
и складывает их в нашу базу. Сайт раздаёт пользователям свои данные.

Источники крипты: сначала Binance (везде, кроме дата-центров США,
где Binance отвечает 451/403), при недоступности — Kraken.
У каждого источника свой формат ответа, см. _binance_* и _kraken_*.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import requests
from django.utils import timezone as dj_timezone

from .models import Asset, Candle

BINANCE_API = "https://api.binance.com"
FRANKFURTER_API = "https://api.frankfurter.app"
KRAKEN_API = "https://api.kraken.com/0/public"
TIMEOUT = 15
CRYPTO_INTERVALS = ("1h", "1d")
FOREX_HISTORY_DAYS = 180

# Kraken не торгует BNB, поэтому вместо него ADA.
# Вторым элементом — «наследственный» код пары в ответах Kraken
# (XBT там возвращается как XXBTZUSD).
KRAKEN_PAIRS = {
    "BTC": ("XBTUSD", "XXBTZUSD"),
    "ETH": ("ETHUSD", "XETHZUSD"),
    "SOL": ("SOLUSD", "SOLUSD"),
    "ADA": ("ADAUSD", "ADAUSD"),
}
KRAKEN_INTERVALS = {"1h": 60, "1d": 1440}


def _to_utc(ms_or_iso):
    """Binance отдаёт миллисекунды, Kraken — секунды, Frankfurter — дату."""
    if isinstance(ms_or_iso, (int, float)):
        return datetime.fromtimestamp(ms_or_iso / 1000, tz=timezone.utc)
    return datetime.fromisoformat(ms_or_iso).replace(tzinfo=timezone.utc)


# ---------- Крипто: Binance ----------

def _binance_quotes(assets):
    """Один пачечный запрос 24ч-тикеров Binance для всех крипто-активов."""
    symbols = ",".join(f'"{a.ticker}"' for a in assets)
    resp = requests.get(
        f"{BINANCE_API}/api/v3/ticker/24hr",
        params={"symbols": f"[{symbols}]"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    quotes = {q["symbol"]: q for q in resp.json()}
    now = dj_timezone.now()
    for asset in assets:
        quote = quotes.get(asset.ticker)
        if not quote:
            continue
        asset.current_price = Decimal(quote["lastPrice"])
        asset.change_24h = Decimal(quote["priceChangePercent"])
        asset.updated_at = now
    Asset.objects.bulk_update(assets, ["current_price", "change_24h", "updated_at"])


def _binance_candles(asset, interval, limit=200):
    resp = requests.get(
        f"{BINANCE_API}/api/v3/klines",
        params={"symbol": asset.ticker, "interval": interval, "limit": limit},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    candles = [
        Candle(
            asset=asset,
            interval=interval,
            timestamp=_to_utc(row[0]),
            open=row[1],
            high=row[2],
            low=row[3],
            close=row[4],
            volume=row[5],
        )
        for row in resp.json()
    ]
    Candle.objects.bulk_create(candles, ignore_conflicts=True)


# ---------- Крипто: Kraken (запасной, работает в США) ----------

def _kraken_quotes(assets):
    """Котировки Kraken: последняя цена + изменение с открытия дня (UTC)."""
    kraken_assets = [a for a in assets if a.symbol in KRAKEN_PAIRS]
    if not kraken_assets:
        return
    pairs = ",".join(KRAKEN_PAIRS[a.symbol][0] for a in kraken_assets)
    resp = requests.get(f"{KRAKEN_API}/Ticker", params={"pair": pairs}, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()["result"]
    now = dj_timezone.now()
    for asset in kraken_assets:
        data = None
        for key in KRAKEN_PAIRS[asset.symbol]:
            data = result.get(key)
            if data:
                break
        if not data:
            continue
        asset.current_price = Decimal(data["c"][0])  # c = [last, ...]
        day_open = Decimal(data["o"])
        asset.change_24h = ((asset.current_price - day_open) / day_open * 100).quantize(
            Decimal("0.01")
        )
        asset.updated_at = now
    Asset.objects.bulk_update(kraken_assets, ["current_price", "change_24h", "updated_at"])


def _kraken_candles(asset, interval, limit=200):
    """Свечи Kraken: [time, open, high, low, close, vwap, volume, count]."""
    pair = KRAKEN_PAIRS[asset.symbol][0]
    resp = requests.get(
        f"{KRAKEN_API}/OHLC",
        params={"pair": pair, "interval": KRAKEN_INTERVALS[interval]},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    result = resp.json()["result"]
    rows = next(v for k, v in result.items() if k != "last")  # там ровно одна пара
    candles = [
        Candle(
            asset=asset,
            interval=interval,
            timestamp=datetime.fromtimestamp(int(row[0]), tz=timezone.utc),
            open=row[1],
            high=row[2],
            low=row[3],
            close=row[4],
            volume=row[6],
        )
        for row in rows[-limit:]
    ]
    Candle.objects.bulk_create(candles, ignore_conflicts=True)


# ---------- Крипто: фасад с автопереключением источника ----------

def fetch_crypto_quotes(assets):
    """Котировки: пробуем Binance, при недоступности — Kraken."""
    try:
        _binance_quotes(assets)
    except requests.RequestException:
        _kraken_quotes(assets)


def fetch_crypto_candles(asset, interval, limit=200):
    """Свечи: пробуем Binance, при недоступности — Kraken."""
    try:
        _binance_candles(asset, interval, limit)
    except requests.RequestException:
        _kraken_candles(asset, interval, limit)


# ---------- Валюты: Frankfurter (данные ЕЦБ) ----------

def fetch_forex_data(asset, days=FOREX_HISTORY_DAYS):
    """Frankfurter: одним запросом тянем дневные курсы за полгода.

    У валютных пар нет внутридневных свечей (данные ЕЦБ обновляются раз в день),
    поэтому интервал только '1d', а open=high=low=close.
    """
    base, quote = asset.ticker[:3], asset.ticker[3:]  # EURUSD -> EUR/USD
    end = date.today()
    start = end - timedelta(days=days)
    resp = requests.get(
        f"{FRANKFURTER_API}/{start}..{end}",
        params={"from": base, "to": quote},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    rates = resp.json()["rates"]  # {"2026-11-20": {"USD": 1.09}, ...}

    candles = [
        Candle(
            asset=asset,
            interval="1d",
            timestamp=_to_utc(day),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=0,
        )
        for day, quote_rates in rates.items()
        for price in [Decimal(str(quote_rates[quote]))]
    ]
    Candle.objects.bulk_create(candles, ignore_conflicts=True)

    closes = sorted((day, Decimal(str(r[quote]))) for day, r in rates.items())
    if not closes:
        return
    asset.current_price = closes[-1][1]
    asset.updated_at = dj_timezone.now()
    if len(closes) >= 2:
        change = (closes[-1][1] - closes[-2][1]) / closes[-2][1] * 100
        asset.change_24h = change.quantize(Decimal("0.01"))
    asset.save()


# ---------- Оркестратор ----------

def update_market_data():
    """Обновляет котировки и свечи всех активов. Возвращает список ошибок."""
    errors = []
    assets = list(Asset.objects.filter(is_active=True))
    crypto = [a for a in assets if a.asset_type == Asset.AssetType.CRYPTO]
    forex = [a for a in assets if a.asset_type == Asset.AssetType.FOREX]

    if crypto:
        try:
            fetch_crypto_quotes(crypto)
        except requests.RequestException as exc:
            errors.append(f"котировки крипты (Binance и Kraken недоступны): {exc}")
        for asset in crypto:
            for interval in CRYPTO_INTERVALS:
                try:
                    fetch_crypto_candles(asset, interval)
                except requests.RequestException as exc:
                    errors.append(f"свечи {asset.symbol} {interval}: {exc}")

    for asset in forex:
        try:
            fetch_forex_data(asset)
        except requests.RequestException as exc:
            errors.append(f"данные {asset.symbol}: {exc}")

    return errors
