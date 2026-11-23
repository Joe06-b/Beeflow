from django.urls import path

from . import views

app_name = "produits_front"

urlpatterns = [
    path("", views.liste_produits, name="liste"),
    path("ajouter/", views.ajouter_produit, name="ajouter"),
    path("<int:pk>/", views.detail_produit, name="detail"),
    path("<int:pk>/code-barres.png", views.image_code_barre, name="code_barre_image"),
    path("<int:pk>/modifier/", views.modifier_produit, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_produit, name="supprimer"),
]
