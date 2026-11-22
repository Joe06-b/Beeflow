from django.urls import path

from .views import (
    RucheCreateView,
    RucheDeleteView,
    RucheDetailView,
    RucheExportPdfView,
    RucheListView,
    RucheHistoriqueView,
    HistoriqueRucheDeleteView,
    RucheStatistiquesView,
    RucheUpdateView,
    RucheFrontListView,
    RucheFrontDetailView,
)

app_name = "ruches"

urlpatterns = [
    path("", RucheListView.as_view(), name="liste"),
    path("statistiques/", RucheStatistiquesView.as_view(), name="statistiques"),
    path("historique/", RucheHistoriqueView.as_view(), name="historique"),
    path(
        "historique/<int:pk>/supprimer/",
        HistoriqueRucheDeleteView.as_view(),
        name="supprimer_historique",
    ),
    path("exporter-pdf/", RucheExportPdfView.as_view(), name="exporter_pdf"),
    path("ajouter/", RucheCreateView.as_view(), name="ajouter"),
    path("<int:pk>/", RucheDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", RucheUpdateView.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", RucheDeleteView.as_view(), name="supprimer"),
]
