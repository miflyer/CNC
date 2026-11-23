from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("prices/", views.prices_json, name="prices"),
    path("update-prices/<str:token>/", views.price_update_trigger, name="price_update_trigger"),
    path("asset/<str:symbol>/", views.asset_detail, name="asset_detail"),
    path("asset/<str:symbol>/candles/", views.asset_candles, name="asset_candles"),
]
