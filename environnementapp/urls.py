from django.urls import path

from . import meteo_pages, meteo_views, views

app_name = "environnement"

urlpatterns = [
    path("meteo/", meteo_pages.fo_meteo, name="meteo"),
    path("api/meteo/zones/", meteo_views.api_liste_zones, name="api_zones_meteo"),
    path(
        "api/meteo/zones/<int:pk>/",
        meteo_views.api_meteo_zone,
        name="api_meteo_zone",
    ),
    path(
        "api/meteo/zones/<int:pk>/actualiser/",
        meteo_views.api_actualiser_meteo,
        name="api_actualiser_meteo",
    ),
    path("", views.liste_environnements, name="liste"),
    path("ajouter/", views.ajouter_environnement, name="ajouter"),
    path("<int:pk>/", views.detail_environnement, name="detail"),
    path("<int:pk>/modifier/", views.modifier_environnement, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_environnement, name="supprimer"),
]
