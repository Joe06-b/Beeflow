from django.urls import path

from . import views_backoffice as views

app_name = "suivi_sanitaire_bo"

urlpatterns = [
    path("", views.bo_liste, name="liste"),
    path("ajouter/", views.bo_ajouter, name="ajouter"),
    path("<int:pk>/modifier/", views.bo_modifier, name="modifier"),
    path("<int:pk>/supprimer/", views.bo_supprimer, name="supprimer"),
    path("supprimer-selection/", views.bo_supprimer_selection, name="supprimer_selection"),
    path("statistiques/", views.bo_statistiques, name="statistiques"),
    path("export-csv/", views.bo_export_csv, name="export_csv"),
]