from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from accounts.models import Wallet
from trading.models import Order, Position, Trade
from trading.services import to_money

# Должен совпадать с default в Wallet.balance (стартовый капитал игрока)
START_BALANCE = Decimal("10000")


@login_required
def portfolio(request):
    wallet = Wallet.objects.get(user=request.user)
    rows = []
    for p in Position.objects.filter(user=request.user, quantity__gt=0).select_related("asset"):
        price = p.asset.current_price or Decimal(0)
        rows.append({
            "position": p,
            "price": price,
            "value": to_money(p.quantity * price),
            "pnl": to_money((price - p.avg_price) * p.quantity),
        })
    positions_value = sum((row["value"] for row in rows), Decimal(0))
    equity = wallet.balance + positions_value
    pnl = equity - START_BALANCE
    pnl_percent = (pnl / START_BALANCE * 100).quantize(Decimal("0.01"))
    pending_orders = Order.objects.filter(user=request.user, status=Order.Status.PENDING).select_related("asset")
    return render(request, "portfolio/portfolio.html", {
        "wallet": wallet,
        "rows": rows,
        "positions_value": positions_value,
        "equity": equity,
        "pnl": pnl,
        "pnl_percent": pnl_percent,
        "pending_orders": pending_orders,
    })


@login_required
def history(request):
    trades = Trade.objects.filter(user=request.user).select_related("asset")
    page_obj = Paginator(trades, 20).get_page(request.GET.get("page"))
    return render(request, "portfolio/history.html", {"page_obj": page_obj})


def leaderboard(request):
    """Публичный рейтинг игроков по капитализации портфеля."""
    rows = []
    for wallet in Wallet.objects.select_related("user"):
        positions_value = Decimal(0)
        for p in Position.objects.filter(user=wallet.user, quantity__gt=0).select_related("asset"):
            price = p.asset.current_price or Decimal(0)
            positions_value += to_money(p.quantity * price)
        equity = wallet.balance + positions_value
        pnl = equity - START_BALANCE
        rows.append({
            "username": wallet.user.username,
            "equity": equity,
            "pnl": pnl,
            "pnl_percent": (pnl / START_BALANCE * 100).quantize(Decimal("0.01")),
        })
    rows.sort(key=lambda row: row["equity"], reverse=True)
    return render(request, "portfolio/leaderboard.html", {"rows": rows})
