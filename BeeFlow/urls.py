"""
URL configuration for BeeFlow project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # FRONTOFFICE
    # Site web (photo de l'apiculteur) : page d'entrée / connexion
    path(
        "",
        TemplateView.as_view(template_name="frontoffice/accueil.html"),
        name="accueil",
    ),
    # Espace apiculteur : la ruche 3D, une face par module
    path(
        "espace/",
        TemplateView.as_view(template_name="frontoffice/espace.html"),
        name="espace",
    ),

    # BACKOFFICE
    path(
        "dashboard/",
        TemplateView.as_view(
            template_name="backoffice/dashboard.html",
            extra_context={"page_title": "Tableau de bord", "active_page": "dashboard"},
        ),
        name="dashboard",
    ),

    # MODULE SUIVI SANITAIRE
    path("suivis/", include("SuiviSanitaireApp.urls")),
    path("dashboard/suivis/", include("SuiviSanitaireApp.urls_backoffice")),
]
