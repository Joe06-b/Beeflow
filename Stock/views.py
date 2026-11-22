from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StockForm
from .models import Stock


def stock_disponibilite(request):
    """Expose uniquement la disponibilite publique des produits en stock."""
    lignes = Stock.objects.values("produit", "unite").annotate(
        quantite=Sum("quantite"),
        seuil=Sum("seuil_alerte"),
    ).order_by("produit", "unite")
    noms_produits = dict(Stock.TYPE_PRODUIT)
    noms_unites = dict(Stock.UNITES)
    icones = {
        "miel": "🍯",
        "cire": "🕯️",
        "pollen": "🌼",
        "propolis": "🌿",
        "gelee_royale": "👑",
    }
    disponibilites = []
    for ligne in lignes:
        quantite = ligne["quantite"] or 0
        seuil = ligne["seuil"] or 0
        if quantite <= 0:
            etat = "epuise"
        elif quantite <= seuil:
            etat = "bientot_epuise"
        else:
            etat = "disponible"
        disponibilites.append({
            "libelle_produit": noms_produits.get(ligne["produit"], ligne["produit"]),
            "libelle_unite": noms_unites.get(ligne["unite"], ligne["unite"]),
            "unite": ligne["unite"],
            "quantite": quantite,
            "icone": icones.get(ligne["produit"], "📦"),
            "etat_disponibilite": etat,
        })
    return render(request, "Stock/disponibilite.html", {
        "disponibilites": disponibilites,
        "page_title": "Disponibilite des produits",
    })


def stock_gestion_frontoffice(request):
    stocks = list(Stock.objects.all().order_by("produit", "emplacement"))
    return render(request, "Stock/front_gestion.html", {
        "stocks": stocks,
        "types_produit": Stock.TYPE_PRODUIT,
        "page_title": "Gestion du stock",
    })


def stock_ajouter_frontoffice(request):
    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Le stock a ete ajoute avec succes.")
            return redirect("stock_gestion_frontoffice")
    else:
        form = StockForm()
    return render(request, "Stock/front_form.html", {
        "form": form,
        "titre": "Ajouter un stock",
        "page_title": "Ajouter un stock",
    })


def stock_modifier_frontoffice(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, "Le stock a ete modifie avec succes.")
            return redirect("stock_gestion_frontoffice")
    else:
        form = StockForm(instance=stock)
    return render(request, "Stock/front_form.html", {
        "form": form,
        "titre": "Modifier le stock",
        "page_title": "Modifier le stock",
    })


def stock_supprimer_frontoffice(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        stock.delete()
        messages.success(request, "Le stock a ete supprime avec succes.")
        return redirect("stock_gestion_frontoffice")
    return render(request, "Stock/front_confirmer_suppression.html", {
        "stock": stock,
        "page_title": "Supprimer un stock",
    })


@staff_member_required
def stock_liste(request):
    stocks = list(Stock.objects.all().order_by("produit", "emplacement"))
    nb_stocks = len(stocks)
    nb_alertes = sum(stock.etat_disponibilite() != "disponible" for stock in stocks)
    nb_epuises = sum(stock.etat_disponibilite() == "epuise" for stock in stocks)
    taux_moyen = round(
        sum(stock.taux_remplissage() for stock in stocks) / nb_stocks,
        1,
    ) if nb_stocks else 0

    sommes_par_unite = {}
    libelles_unites = dict(Stock.UNITES)
    for stock in stocks:
        sommes_par_unite[stock.unite] = sommes_par_unite.get(stock.unite, 0) + stock.quantite
    quantites_totales = [
        {"unite": libelles_unites.get(unite, unite), "quantite": quantite}
        for unite, quantite in sommes_par_unite.items()
    ]

    return render(request, "Stock/liste.html", {
        "stocks": stocks,
        "nb_stocks": nb_stocks,
        "nb_alertes": nb_alertes,
        "nb_epuises": nb_epuises,
        "taux_moyen": taux_moyen,
        "quantites_totales": quantites_totales,
        "types_produit": Stock.TYPE_PRODUIT,
        "active_page": "stock",
        "page_title": "Gestion du stock",
    })


@staff_member_required
def stock_detail(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    return render(request, "Stock/detail.html", {
        "stock": stock,
        "active_page": "stock",
        "page_title": "Détail du stock",
    })


@staff_member_required
def stock_tableau_de_bord(request):
    stocks = list(Stock.objects.all().order_by("produit", "emplacement"))
    quantites = {}
    emplacements = {}
    alertes = []

    for stock in stocks:
        cle_quantite = (stock.libelle_produit(), stock.get_unite_display())
        quantites[cle_quantite] = quantites.get(cle_quantite, 0) + stock.quantite

        emplacement = stock.emplacement.strip() or "Non précisé"
        emplacements[emplacement] = emplacements.get(emplacement, 0) + 1

        if stock.etat_disponibilite() != "disponible":
            alertes.append(stock)

    taux_moyen = round(
        sum(stock.taux_remplissage() for stock in stocks) / len(stocks),
        1,
    ) if stocks else 0

    chart_data = {
        "quantites": {
            "labels": [f"{produit} ({unite})" for produit, unite in quantites],
            "values": [float(quantite) for quantite in quantites.values()],
        },
        "remplissage": {
            "labels": [
                f"{stock.libelle_produit()} · {stock.emplacement or 'Non précisé'} · #{stock.pk}"
                for stock in stocks
            ],
            "values": [stock.taux_remplissage() for stock in stocks],
        },
        "emplacements": {
            "labels": list(emplacements.keys()),
            "values": list(emplacements.values()),
        },
    }

    return render(request, "Stock/tableau_de_bord.html", {
        "stocks": stocks,
        "alertes": alertes,
        "nb_stocks": len(stocks),
        "nb_alertes": len(alertes),
        "taux_moyen": taux_moyen,
        "chart_data": chart_data,
        "active_page": "stock",
        "page_title": "Tableau de bord Stock",
    })


@staff_member_required
def stock_ajouter(request):
    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Le stock a été ajouté avec succès.")
            return redirect("stock_liste")
    else:
        form = StockForm()
    return render(request, "Stock/form.html", {
        "form": form,
        "titre": "Ajouter un stock",
        "active_page": "stock",
        "page_title": "Ajouter un stock",
    })


@staff_member_required
def stock_modifier(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, "Le stock a été modifié avec succès.")
            return redirect("stock_liste")
    else:
        form = StockForm(instance=stock)
    return render(request, "Stock/form.html", {
        "form": form,
        "titre": "Modifier le stock",
        "active_page": "stock",
        "page_title": "Modifier le stock",
    })


@staff_member_required
def stock_supprimer(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == "POST":
        stock.delete()
        messages.success(request, "Le stock a été supprimé avec succès.")
        return redirect("stock_liste")
    return render(request, "Stock/confirmer_suppression.html", {
        "stock": stock,
        "active_page": "stock",
        "page_title": "Supprimer un stock",
    })
