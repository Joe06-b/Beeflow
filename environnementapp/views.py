
"""
Vues FRONTOFFICE du module Gestion des Environnements.
Recherche, filtres et tri.
"""

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EnvironnementForm, RechercheEnvironnementForm
from .models import Environnement
from .services import filtrer_environnements


TEMPLATE_DIR = "frontoffice/environnementapp/"


# ---------------------------------------------------------------------------
# Liste des zones environnementales avec recherche, filtres et tri
# ---------------------------------------------------------------------------

def liste_environnements(request):
    form = RechercheEnvironnementForm(request.GET or None)

    if form.is_valid():
        donnees = form.cleaned_data
    else:
        donnees = {}

    zones = filtrer_environnements(donnees)

    # Statistiques globales : indépendantes des filtres
    toutes_les_zones = Environnement.objects.all()

    nb_total = toutes_les_zones.count()

    surface_totale = (
        toutes_les_zones.aggregate(total=Sum("surface"))["total"] or 0
    )

    nb_vegetations = (
        toutes_les_zones.values("typeVegetation").distinct().count()
    )

    # Conservation des paramètres GET pour les liens de pagination
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "form": form,
        "zones": zones,
        "nb_total": nb_total,
        "nb_resultats": zones.count(),
        "surface_totale": round(surface_totale, 1),
        "nb_vegetations": nb_vegetations,
        "params": params.urlencode(),
    }

    return render(
        request,
        TEMPLATE_DIR + "liste.html",
        context,
    )


# ---------------------------------------------------------------------------
# Détail d'une zone
# ---------------------------------------------------------------------------

def detail_environnement(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)

    return render(
        request,
        TEMPLATE_DIR + "detail.html",
        {"zone": zone},
    )


# ---------------------------------------------------------------------------
# Ajouter une zone
# ---------------------------------------------------------------------------

def ajouter_environnement(request):
    if request.method == "POST":
        form = EnvironnementForm(request.POST)

        if form.is_valid():
            zone = form.save()

            messages.success(
                request,
                f"La zone n°{zone.idZone} a été ajoutée avec succès.",
            )

            return redirect("environnement:detail", pk=zone.pk)

        messages.error(
            request,
            "Le formulaire contient des erreurs. Veuillez les corriger.",
        )

    else:
        form = EnvironnementForm()

    return render(
        request,
        TEMPLATE_DIR + "form.html",
        {
            "form": form,
            "titre": "Ajouter une zone environnementale",
            "mode": "ajout",
        },
    )


# ---------------------------------------------------------------------------
# Modifier une zone
# ---------------------------------------------------------------------------

def modifier_environnement(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)

    if request.method == "POST":
        form = EnvironnementForm(request.POST, instance=zone)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                f"La zone n°{zone.idZone} a été modifiée avec succès.",
            )

            return redirect("environnement:detail", pk=zone.pk)

        messages.error(
            request,
            "Le formulaire contient des erreurs. Veuillez les corriger.",
        )

    else:
        form = EnvironnementForm(instance=zone)

    return render(
        request,
        TEMPLATE_DIR + "form.html",
        {
            "form": form,
            "zone": zone,
            "titre": f"Modifier {zone.nomZone}",
            "mode": "modification",
        },
    )


# ---------------------------------------------------------------------------
# Supprimer une zone
# ---------------------------------------------------------------------------

def supprimer_environnement(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)

    if request.method == "POST":
        numero = zone.idZone
        zone.delete()

        messages.success(
            request,
            f"La zone n°{numero} a été supprimée.",
        )

        return redirect("environnement:liste")

    return render(
        request,
        TEMPLATE_DIR + "confirmer_suppression.html",
        {"zone": zone},
    )
