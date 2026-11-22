"""
Vues du BACK OFFICE (administration) : Gestion des produits.
Toutes protégées par @admin_requis (statique pour l'instant, voir SuiviSanitaireApp/decorators.py).
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from SuiviSanitaireApp.decorators import admin_requis

from .forms import ProduitForm
from .models import Produit
from .services import contexte_liste, statistiques_produits

TEMPLATE_DIR = "backoffice/produits/"


def _contexte(page_title, **extra):
    """Variables attendues par base_backoffice.html (titre + élément actif de la sidebar)."""
    return {"page_title": page_title, "active_page": "production", **extra}


# READ : liste de gestion
@admin_requis
def bo_liste(request):
    return render(request, TEMPLATE_DIR + "liste.html", _contexte("Gestion des produits", **contexte_liste(request)))


# READ : détail
@admin_requis
def bo_detail(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    return render(request, TEMPLATE_DIR + "detail.html", _contexte("Détail du produit", produit=produit))


# CREATE
@admin_requis
def bo_ajouter(request):
    form = ProduitForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            produit = form.save()
            messages.success(request, f"Produit #{produit.pk} ajouté.")
            return redirect("produits:liste")
        messages.error(request, "Le formulaire contient des erreurs.")
    return render(request, TEMPLATE_DIR + "form.html", _contexte("Ajouter un produit", form=form, mode="ajout"))


# UPDATE
@admin_requis
def bo_modifier(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    form = ProduitForm(request.POST or None, request.FILES or None, instance=produit)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f"Produit #{produit.pk} modifié.")
            return redirect("produits:liste")
        messages.error(request, "Le formulaire contient des erreurs.")
    return render(request, TEMPLATE_DIR + "form.html", _contexte(
        "Modifier le produit", form=form, produit=produit, mode="modification",
    ))


# DELETE (GET = confirmation, POST = suppression)
@admin_requis
@require_http_methods(["GET", "POST"])
def bo_supprimer(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == "POST":
        numero = produit.pk
        produit.delete()
        messages.success(request, f"Produit #{numero} supprimé.")
        return redirect("produits:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", _contexte("Supprimer le produit", produit=produit))


# STATISTIQUES (onglet à côté de « Gestion de production »)
@admin_requis
def bo_statistiques(request):
    return render(request, TEMPLATE_DIR + "statistiques.html", _contexte(
        "Statistiques des produits", stats=statistiques_produits(), onglet="stats"))


# Données JSON : utilisées par la page Statistiques pour se rafraîchir automatiquement
@admin_requis
def bo_statistiques_donnees(request):
    return JsonResponse(statistiques_produits())
