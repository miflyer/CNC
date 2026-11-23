from django.urls import path

from . import views

urlpatterns = [
    path("portfolio/", views.portfolio, name="portfolio"),
    path("history/", views.history, name="history"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
]
