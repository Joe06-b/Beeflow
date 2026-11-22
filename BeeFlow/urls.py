"""
URL configuration for BeeFlow project.
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.views.generic import TemplateView
from BeeFlow import settings
from UtilisateursApp import views as user_views
from .views import EspaceView,DashboardView

urlpatterns = [
    path("", TemplateView.as_view(template_name="frontoffice/accueil.html"), name="accueil"),
    path("espace/", EspaceView.as_view(), name="espace"),
    path('admin/', admin.site.urls),

    path('comptes/login/',user_views.BeeFlowLoginView.as_view(),name='login'),
    path('comptes/', include('django.contrib.auth.urls')),
    path('comptes/login/face/', user_views.login_face_api, name='login_face_api'),
    path('comptes/premiere-connexion/', user_views.premiere_connexion_view, name='premiere_connexion'),
    path('comptes/dispatch-connexion/', user_views.dispatch_apres_connexion, name='dispatch_connexion'),

    path('dashboard/utilisateurs/', include('UtilisateursApp.urls')),
    path("dashboard/",DashboardView.as_view(),name="dashboard"),
    path("suivis/", include("SuiviSanitaireApp.urls")),
    path("dashboard/suivis/", include("SuiviSanitaireApp.urls_backoffice")),
    path("ruches/", include("rucheapp.urls_frontoffice")),
    path("dashboard/ruches/", include("rucheapp.urls")),
    
    path("produits/", include("ProduitApp.urls")),
        path("dashboard/produits/", include("ProduitApp.urls_backoffice")),
]
    
    # Photos des produits (en développement)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)