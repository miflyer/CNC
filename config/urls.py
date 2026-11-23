from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("market.urls")),
    path("", include("trading.urls")),
    path("", include("portfolio.urls")),
]
