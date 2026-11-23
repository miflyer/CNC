from django.contrib import admin

from .models import Order, Position, Trade


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "asset", "side", "order_type", "status", "quantity", "price", "created_at")
    list_filter = ("status", "order_type", "side", "asset")


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "asset", "side", "quantity", "price", "total", "created_at")
    list_filter = ("side", "asset")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "quantity", "avg_price")
