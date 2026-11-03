from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"), #index здесь это имя маршрута
]
