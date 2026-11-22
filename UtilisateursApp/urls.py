
from django.urls import path
from . import views

app_name = 'utilisateurs'

urlpatterns = [
    path('', views.UtilisateurListView.as_view(), name='liste'),
    path('statistiques/', views.UtilisateurStatistiquesView.as_view(), name='statistiques'),
    path('export-csv/', views.utilisateur_export_csv, name='export_csv'),
    path('ajouter/', views.UtilisateurCreateView.as_view(), name='ajouter'),
    path('<int:pk>/', views.UtilisateurDetailView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.UtilisateurUpdateView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.UtilisateurDeleteView.as_view(), name='supprimer'),
    path('modifier-mon-compte/',views.ModifierMonCompteView.as_view(),name='modifier_mon_compte'),
    path('supprimer-mon-compte/',views.SupprimerMonCompteView.as_view(),name='supprimer_mon_compte'),
]
