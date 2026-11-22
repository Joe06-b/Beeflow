from django.urls import path

from . import views

app_name = "suivi_sanitaire"

urlpatterns = [
    path("", views.liste_suivis, name="liste"),
    path("ajouter/", views.ajouter_suivi, name="ajouter"),
    path("alertes/", views.alertes_suivis, name="alertes"),
    path("alertes/compte/", views.alertes_compte, name="alertes_compte"),
    path("<int:pk>/", views.detail_suivi, name="detail"),
    path("<int:pk>/modifier/", views.modifier_suivi, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_suivi, name="supprimer"),
]
