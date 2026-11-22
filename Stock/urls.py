from django.urls import path
from . import views

urlpatterns = [
    path('disponibilite/', views.stock_disponibilite, name='stock_disponibilite'),
    path('gestion-frontoffice/', views.stock_gestion_frontoffice, name='stock_gestion_frontoffice'),
    path('gestion-frontoffice/ajouter/', views.stock_ajouter_frontoffice, name='stock_ajouter_frontoffice'),
    path('gestion-frontoffice/<int:pk>/modifier/', views.stock_modifier_frontoffice, name='stock_modifier_frontoffice'),
    path('gestion-frontoffice/<int:pk>/supprimer/', views.stock_supprimer_frontoffice, name='stock_supprimer_frontoffice'),
    path('', views.stock_liste, name='stock_liste'),
    path('ajouter/', views.stock_ajouter, name='stock_ajouter'),
    path('tableau-de-bord/', views.stock_tableau_de_bord, name='stock_tableau_de_bord'),
    path('<int:pk>/', views.stock_detail, name='stock_detail'),
    path('<int:pk>/modifier/', views.stock_modifier, name='stock_modifier'),
    path('<int:pk>/supprimer/', views.stock_supprimer, name='stock_supprimer'),
]
