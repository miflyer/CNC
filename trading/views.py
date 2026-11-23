from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .forms import TradeForm
from .models import Order
from .services import cancel_order, execute_market_order, place_limit_order


@login_required
@require_POST
def place_order(request):
    form = TradeForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        try:
            if data["order_type"] == Order.Type.MARKET:
                execute_market_order(request.user, data["asset"].pk, data["side"], data["quantity"])
                messages.success(request, "Сделка исполнена по рыночной цене")
            else:
                place_limit_order(
                    request.user, data["asset"].pk, data["side"],
                    data["quantity"], data["limit_price"],
                )
                messages.success(request, "Лимитная заявка размещена")
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
    else:
        messages.error(request, "Проверьте данные заявки")
    return redirect("asset_detail", symbol=form.data.get("asset_symbol", ""))


@login_required
@require_POST
def cancel_order_view(request, order_id):
    try:
        cancel_order(request.user, order_id)
        messages.success(request, "Заявка отменена, средства возвращены")
    except (ValidationError, Order.DoesNotExist) as exc:
        messages.error(request, getattr(exc, "messages", [str(exc)])[0])
    order = get_object_or_404(Order, pk=order_id)
    return redirect("asset_detail", symbol=order.asset.symbol)
