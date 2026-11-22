"""Vues du FRONT OFFICE (espace apiculteur) : Gestion des produits."""
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ProduitForm
from .models import Produit
from .services import contexte_liste, png_code_barre

TEMPLATE_DIR = "frontoffice/produits/"


# READ : liste (recherche, filtres, tri, pagination)
def liste_produits(request):
    return render(request, TEMPLATE_DIR + "liste.html", contexte_liste(request))


# Image PNG du code-barres EAN-13 (utilisée par le front office ET le back office)
def image_code_barre(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    code = (produit.code_barre or "").strip()
    if len(code) != 13 or not code.isdigit():
        raise Http404("Code-barres indisponible")
    try:
        contenu = png_code_barre(code)
    except ImportError as exc:
        raise Http404("Installez python-barcode et Pillow pour afficher le code-barres.") from exc
    response = HttpResponse(contenu, content_type="image/png")
    response["Cache-Control"] = "public, max-age=86400"
    return response


# READ : détail
def detail_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    return render(request, TEMPLATE_DIR + "detail.html", {"produit": produit})


# CREATE
def ajouter_produit(request):
    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save()
            messages.success(request, "Le produit a été ajouté avec succès.")
            return redirect("produits_front:detail", pk=produit.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.")
    else:
        form = ProduitForm()
    return render(request, TEMPLATE_DIR + "form.html", {"form": form, "titre": "Ajouter un produit", "mode": "ajout"})


# UPDATE
def modifier_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, "Le produit a été modifié avec succès.")
            return redirect("produits_front:detail", pk=produit.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.")
    else:
        form = ProduitForm(instance=produit)
    return render(request, TEMPLATE_DIR + "form.html", {
        "form": form, "produit": produit, "titre": "Modifier le produit", "mode": "modification",
    })


# DELETE (GET = page de confirmation, POST = suppression)
@require_http_methods(["GET", "POST"])
def supprimer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == "POST":
        produit.delete()
        messages.success(request, "Le produit a été supprimé.")
        return redirect("produits_front:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", {"produit": produit})
