from django.urls import path

from .views import (
    RucheFrontCreateView,
    RucheFrontDeleteView,
    RucheFrontDetailView,
    RucheFrontListView,
    RucheFrontUpdateView,
)

app_name = "ruches_front"

urlpatterns = [
    path("", RucheFrontListView.as_view(), name="liste"),
    path("ajouter/", RucheFrontCreateView.as_view(), name="ajouter"),
    path("<int:pk>/modifier/", RucheFrontUpdateView.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", RucheFrontDeleteView.as_view(), name="supprimer"),
    path("<int:pk>/", RucheFrontDetailView.as_view(), name="detail"),
]
