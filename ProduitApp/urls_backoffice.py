from django.urls import path

from . import views, views_backoffice as bo

app_name = "produits"

urlpatterns = [
    path("", bo.bo_liste, name="liste"),
    path("statistiques/", bo.bo_statistiques, name="statistiques"),
    path("statistiques/donnees/", bo.bo_statistiques_donnees, name="statistiques_donnees"),
    path("ajouter/", bo.bo_ajouter, name="ajouter"),
    path("<int:pk>/", bo.bo_detail, name="detail"),
    # Même image que le front office (une seule vue)
    path("<int:pk>/code-barres.png", views.image_code_barre, name="code_barre_image"),
    path("<int:pk>/modifier/", bo.bo_modifier, name="modifier"),
    path("<int:pk>/supprimer/", bo.bo_supprimer, name="supprimer"),
]
