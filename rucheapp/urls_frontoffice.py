from django.urls import path

from .views import (
    RucheFrontCreateView,
    RucheFrontDetailView,
    RucheFrontListView,
)

app_name = "ruches_front"

urlpatterns = [
    path("", RucheFrontListView.as_view(), name="liste"),
    path("ajouter/", RucheFrontCreateView.as_view(), name="ajouter"),
    path("<int:pk>/", RucheFrontDetailView.as_view(), name="detail"),
]
