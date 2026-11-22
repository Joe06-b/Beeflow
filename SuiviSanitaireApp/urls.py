from django.urls import path

from . import views

app_name = "suivi_sanitaire"

urlpatterns = [
    path("", views.liste_suivis, name="liste"),
    path("ajouter/", views.ajouter_suivi, name="ajouter"),
    path("alertes/", views.alertes_suivis, name="alertes"),
    path("alertes/compte/", views.alertes_compte, name="alertes_compte"),
    path("maladies/", views.atlas_maladies, name="atlas"),
    path("maladies/<slug:slug>/3d/", views.maladie_3d, name="maladie_3d"),
    path("maladies/<slug:slug>/evolution/", views.maladie_evolution, name="maladie_evolution"),
    path("<int:pk>/", views.detail_suivi, name="detail"),
    path("<int:pk>/modifier/", views.modifier_suivi, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_suivi, name="supprimer"),
]
