from django.urls import path

from . import meteo_pages, meteo_views, views_backoffice as views

app_name = "environnement_bo"

urlpatterns = [
    path("meteo/", meteo_pages.bo_meteo_liste, name="meteo"),
    path("meteo/<int:pk>/", meteo_pages.bo_meteo_detail, name="meteo_detail"),
    path("api/meteo/zones/", meteo_views.bo_api_liste_zones, name="api_zones_meteo"),
    path(
        "api/meteo/zones/<int:pk>/",
        meteo_views.bo_api_meteo_zone,
        name="api_meteo_zone",
    ),
    path(
        "api/meteo/zones/<int:pk>/actualiser/",
        meteo_views.bo_api_actualiser_meteo,
        name="api_actualiser_meteo",
    ),
    path("", views.bo_liste, name="liste"),
    path("ajouter/", views.bo_ajouter, name="ajouter"),
    path("<int:pk>/", views.bo_detail, name="detail"),
    path("<int:pk>/modifier/", views.bo_modifier, name="modifier"),
    path("<int:pk>/supprimer/", views.bo_supprimer, name="supprimer"),
    path("supprimer-selection/", views.bo_supprimer_selection, name="supprimer_selection"),
    path("statistiques/", views.bo_statistiques, name="statistiques"),
    path("export-csv/", views.bo_export_csv, name="export_csv"),
]
