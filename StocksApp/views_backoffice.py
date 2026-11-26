"""
Vues du BACK OFFICE (administration) du module Gestion du stock.
Toutes protégées par @admin_requis (voir decorators.py).
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import admin_requis
from .forms import RechercheStockForm, StockForm
from .models import Stock
from .services import calculer_statistiques, filtrer_stocks

TEMPLATE_DIR = "backoffice/stocks/"
PAR_PAGE = 10


def _contexte(page_title, **extra):
    """Variables attendues par base_backoffice.html (titre + élément actif de la sidebar)."""
    return {"page_title": page_title, "active_page": "stock", **extra}


def _filtres(request):
    form = RechercheStockForm(request.GET or None)
    donnees = form.cleaned_data if form.is_valid() else {}
    return (form if form.is_bound else RechercheStockForm()), donnees


# ---------------------------------------------------------------------------
# consulterStocks : recherche, filtres, tri, pagination
# ---------------------------------------------------------------------------
@admin_requis
def bo_liste(request):
    form, donnees = _filtres(request)
    stocks = filtrer_stocks(donnees)
    page = Paginator(stocks, PAR_PAGE).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, TEMPLATE_DIR + "liste.html", _contexte(
        "Gestion du stock",
        form=form,
        page=page,
        nb_resultats=stocks.count(),
        params=params.urlencode(),
        stats=calculer_statistiques(),
    ))


# ---------------------------------------------------------------------------
# ajouterStock / modifierStock
# ---------------------------------------------------------------------------
@admin_requis
def bo_ajouter(request):
    form = StockForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            stock = form.save()
            messages.success(request, f"Stock « {stock.nom_stock} » ajouté.")
            if "enregistrer_et_ajouter" in request.POST:
                return redirect("stocks_bo:ajouter")
            return redirect("stocks_bo:liste")
        messages.error(request, "Le formulaire contient des erreurs.")
    return render(request, TEMPLATE_DIR + "form.html", _contexte("Ajouter un stock", form=form, mode="ajout"))


@admin_requis
def bo_modifier(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    form = StockForm(request.POST or None, instance=stock)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f"Stock « {stock.nom_stock} » modifié.")
            return redirect("stocks_bo:liste")
        messages.error(request, "Le formulaire contient des erreurs.")
    return render(request, TEMPLATE_DIR + "form.html", _contexte(
        f"Modifier le stock « {stock.nom_stock} »", form=form, stock=stock, mode="modification",
    ))


# ---------------------------------------------------------------------------
# supprimerStock (un seul) / supprimer plusieurs
# Les stocks qui contiennent des produits ne sont jamais supprimés.
# ---------------------------------------------------------------------------
@admin_requis
def bo_supprimer(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        if stock.nb_produits:
            messages.error(
                request,
                f"Impossible de supprimer « {stock.nom_stock} » : il contient {stock.nb_produits} produit(s).",
            )
            return redirect("stocks_bo:liste")
        nom = stock.nom_stock
        stock.delete()
        messages.success(request, f"Stock « {nom} » supprimé.")
        return redirect("stocks_bo:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", _contexte("Supprimer un stock", stocks=[stock]))


@admin_requis
@require_POST
def bo_supprimer_selection(request):
    ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
    if not ids:
        messages.warning(request, "Aucun stock sélectionné.")
        return redirect("stocks_bo:liste")

    stocks = list(Stock.objects.filter(pk__in=ids))

    if "confirmer" in request.POST:          # 2e étape : suppression réelle
        supprimables = [s for s in stocks if not s.nb_produits]
        bloques = [s for s in stocks if s.nb_produits]
        for s in supprimables:
            s.delete()
        if supprimables:
            messages.success(request, f"{len(supprimables)} stock(s) supprimé(s).")
        if bloques:
            noms = ", ".join(s.nom_stock for s in bloques)
            messages.warning(request, f"Non supprimé(s) car ils contiennent des produits : {noms}.")
        return redirect("stocks_bo:liste")

    # 1re étape : page de confirmation
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html",
                  _contexte("Supprimer des stocks", stocks=stocks, multiple=True))
