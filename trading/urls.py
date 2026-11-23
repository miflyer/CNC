from django.urls import path

from . import views

urlpatterns = [
    path("trade/", views.place_order, name="place_order"),
    path("orders/<int:order_id>/cancel/", views.cancel_order_view, name="cancel_order"),
]
