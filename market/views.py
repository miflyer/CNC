from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from trading.models import Order, Position

from .models import Asset
from .services import update_market_data

ALLOWED_INTERVALS = ("1h", "1d")


def index(request):
    assets = Asset.objects.filter(is_active=True, current_price__isnull=False).order_by("asset_type", "symbol")
    return render(request, "market/index.html", {"assets": assets})


def asset_detail(request, symbol):
    asset = get_object_or_404(Asset, symbol=symbol.upper(), is_active=True)
    intervals = ["1h", "1d"] if asset.asset_type == Asset.AssetType.CRYPTO else ["1d"]
    context = {"asset": asset, "intervals": intervals, "default_interval": intervals[0]}
    if request.user.is_authenticated:
        context["position"] = Position.objects.filter(user=request.user, asset=asset, quantity__gt=0).first()
        context["pending_orders"] = Order.objects.filter(
            user=request.user, asset=asset, status=Order.Status.PENDING
        )
    return render(request, "market/detail.html", context)


def asset_candles(request, symbol):
    asset = get_object_or_404(Asset, symbol=symbol.upper(), is_active=True)
    interval = request.GET.get("interval", "1d")
    allowed = ["1h", "1d"] if asset.asset_type == Asset.AssetType.CRYPTO else ["1d"]
    if interval not in allowed:
        interval = allowed[0]
    candles = asset.candles.filter(interval=interval)[:300]  # Meta.ordering = timestamp asc
    data = [
        {
            "time": int(c.timestamp.timestamp()),
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
        }
        for c in candles
    ]
    return JsonResponse({"candles": data})


def prices_json(request):
    """Текущие цены всех активов — для polling-обновления на страницах."""
    assets = Asset.objects.filter(is_active=True, current_price__isnull=False)
    return JsonResponse(
        {a.symbol: {"price": f"{a.current_price.normalize():f}", "change": str(a.change_24h or 0)} for a in assets}
    )


def price_update_trigger(request, token):
    """Обновление цен и исполнение лимитных заявок по секретному URL.

    Нужно для бесплатного хостинга: внешний cron (например, cron-job.org)
    периодически дёргает https://<сайт>/update-prices/<токен>/ —
    так цены свежие, а «уснувший» бесплатный сервис просыпается.
    """
    from django.conf import settings
    from django.http import HttpResponseForbidden

    if token != settings.PRICE_UPDATE_TOKEN:
        return HttpResponseForbidden("Неверный токен")

    from trading.services import process_pending_limit_orders

    errors = update_market_data()
    executed = process_pending_limit_orders()
    return JsonResponse({"errors": errors, "limit_orders_executed": executed})
