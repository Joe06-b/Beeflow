from django.urls import path

from . import views

app_name = "stocks"

urlpatterns = [
    path("", views.liste_stocks, name="liste"),
    path("ajouter/", views.ajouter_stock, name="ajouter"),
    path("<int:pk>/", views.detail_stock, name="detail"),
    path("<int:pk>/modifier/", views.modifier_stock, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_stock, name="supprimer"),
]