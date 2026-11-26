"""
Vues du FRONT OFFICE (espace apiculteur) du module Gestion du stock.
Même logique que le back office (forms.py + services.py), présentation différente.
Accès : voir decorators.metier_requis.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import metier_requis
from .forms import RechercheStockForm, StockForm
from .models import Stock
from .services import calculer_statistiques, filtrer_stocks

TEMPLATE_DIR = "frontoffice/stocks/"


# ---------------------------------------------------------------------------
# consulterStocks + rechercherStock + trierStocks
# ---------------------------------------------------------------------------
@metier_requis
def liste_stocks(request):
    form = RechercheStockForm(request.GET or None)
    donnees = form.cleaned_data if form.is_valid() else {}
    stocks = filtrer_stocks(donnees)
    return render(request, TEMPLATE_DIR + "liste.html", {
        "form": form if form.is_bound else RechercheStockForm(),
        "stocks": stocks,
        "nb_resultats": stocks.count(),
        "stats": calculer_statistiques(),
    })


# ---------------------------------------------------------------------------
# consulterStock (détail + produits stockés et leurs volumes)
# ---------------------------------------------------------------------------
@metier_requis
def detail_stock(request, pk):
    stock = get_object_or_404(Stock.objects.prefetch_related("responsables"), pk=pk)
    return render(request, TEMPLATE_DIR + "detail.html", {
        "stock": stock,
        "lignes_produits": stock.produits_avec_volumes(),
    })


# ---------------------------------------------------------------------------
# ajouterStock
# ---------------------------------------------------------------------------
@metier_requis
def ajouter_stock(request):
    form = StockForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            stock = form.save()
            messages.success(request, f"Le stock « {stock.nom_stock} » a été ajouté avec succès.")
            return redirect("stocks:detail", pk=stock.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.")
    return render(request, TEMPLATE_DIR + "form.html", {"form": form, "titre": "Ajouter un stock", "mode": "ajout"})


# ---------------------------------------------------------------------------
# modifierStock
# ---------------------------------------------------------------------------
@metier_requis
def modifier_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    form = StockForm(request.POST or None, instance=stock)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f"Le stock « {stock.nom_stock} » a été modifié avec succès.")
            return redirect("stocks:detail", pk=stock.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.")
    return render(request, TEMPLATE_DIR + "form.html", {
        "form": form, "stock": stock, "titre": f"Modifier le stock « {stock.nom_stock} »", "mode": "modification",
    })


# ---------------------------------------------------------------------------
# supprimerStock (GET = page de confirmation, POST = suppression)
# Un stock qui contient des produits ne peut pas être supprimé.
# ---------------------------------------------------------------------------
@metier_requis
def supprimer_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        if stock.nb_produits:
            messages.error(
                request,
                f"Impossible de supprimer « {stock.nom_stock} » : il contient {stock.nb_produits} produit(s). "
                "Déplacez-les ou supprimez-les d'abord.",
            )
            return redirect("stocks:detail", pk=stock.pk)
        nom = stock.nom_stock
        stock.delete()
        messages.success(request, f"Le stock « {nom} » a été supprimé.")
        return redirect("stocks:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", {"stock": stock})
