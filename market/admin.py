from django.contrib import admin

from .models import Asset, Candle


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "asset_type", "current_price", "change_24h", "updated_at")
    list_filter = ("asset_type", "is_active")
    search_fields = ("symbol", "name", "ticker")


@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ("asset", "interval", "timestamp", "open", "high", "low", "close")
    list_filter = ("interval",)
