
"""
Vues du BACK OFFICE (administration) de la Gestion des Environnements.
Protégées par @admin_requis.
Recherche, filtres avancés, tri, pagination et export CSV.
"""

import csv
import io

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import admin_requis
from .forms import (
    EnvironnementForm,
    RechercheEnvironnementForm,
    StatistiquesEnvironnementForm,
)
from .models import Environnement
from .services import calculer_statistiques_environnement, filtrer_environnements


TEMPLATE_DIR = "backoffice/environnementapp/"
PAR_PAGE = 10


def _contexte(page_title, **extra):
    """Variables attendues par base_backoffice.html."""
    return {
        "page_title": page_title,
        "active_page": "environnement",
        **extra,
    }


def _filtres(request):
    """
    Récupère le formulaire de recherche et ses données validées.
    Les données retournées sont directement utilisables par le service.
    """
    form = RechercheEnvironnementForm(request.GET or None)

    donnees = form.cleaned_data if form.is_valid() else {}

    return form, donnees


# ---------------------------------------------------------------------------
# A. Liste des zones avec recherche, filtres et tri
# ---------------------------------------------------------------------------

@admin_requis
def bo_liste(request):
    form, donnees = _filtres(request)

    zones = filtrer_environnements(donnees)

    # Pagination : 10 résultats par page
    paginator = Paginator(zones, PAR_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    # Conserver tous les filtres dans les liens de pagination
    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        TEMPLATE_DIR + "liste.html",
        _contexte(
            "Gestion des environnements",
            form=form,
            page=page,
            nb_resultats=zones.count(),
            nb_total=Environnement.objects.count(),
            params=params.urlencode(),
        ),
    )


# ---------------------------------------------------------------------------
# B. Ajouter une zone
# ---------------------------------------------------------------------------

@admin_requis
def bo_ajouter(request):
    form = EnvironnementForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST":
        if form.is_valid():
            zone = form.save()

            messages.success(request, f"Zone #{zone.idZone} ajoutée.")

            if "enregistrer_et_ajouter" in request.POST:
                return redirect("environnement_bo:ajouter")

            return redirect("environnement_bo:liste")

        messages.error(
            request,
            "Le formulaire contient des erreurs.",
        )

    return render(
        request,
        TEMPLATE_DIR + "form.html",
        _contexte(
            "Ajouter une zone environnementale",
            form=form,
            mode="ajout",
        ),
    )


# ---------------------------------------------------------------------------
# C. Consulter une zone
# ---------------------------------------------------------------------------

@admin_requis
def bo_detail(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)

    return render(
        request,
        TEMPLATE_DIR + "detail.html",
        _contexte(
            f"Zone : {zone.nomZone}",
            zone=zone,
        ),
    )


# ---------------------------------------------------------------------------
# D. Modifier une zone
# ---------------------------------------------------------------------------

@admin_requis
def bo_modifier(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)

    form = EnvironnementForm(
        request.POST if request.method == "POST" else None,
        instance=zone,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            messages.success(request, f"Zone #{zone.idZone} modifiée.")

            return redirect("environnement_bo:liste")

        messages.error(
            request,
            "Le formulaire contient des erreurs.",
        )

    return render(
        request,
        TEMPLATE_DIR + "form.html",
        _contexte(
            f"Modifier la zone : {zone.nomZone}",
            form=form,
            zone=zone,
            mode="modification",
        ),
    )


# ---------------------------------------------------------------------------
# E. Supprimer une zone (unitaire)
# ---------------------------------------------------------------------------

@admin_requis
def bo_supprimer(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)

    if request.method == "POST":
        numero = zone.idZone

        zone.delete()

        messages.success(request, f"Zone #{numero} supprimée.")

        return redirect("environnement_bo:liste")

    return render(
        request,
        TEMPLATE_DIR + "confirm_delete.html",
        _contexte(
            "Supprimer une zone",
            zones=[zone],
        ),
    )


# ---------------------------------------------------------------------------
# F. Supprimer plusieurs zones (sélection multiple)
# ---------------------------------------------------------------------------

@admin_requis
@require_POST
def bo_supprimer_selection(request):
    ids = [
        i for i in request.POST.getlist("ids")
        if i.isdigit()
    ]

    if not ids:
        messages.warning(
            request,
            "Aucune zone sélectionnée.",
        )
        return redirect("environnement_bo:liste")

    zones = Environnement.objects.filter(pk__in=ids)

    if "confirmer" in request.POST:
        nb, _ = zones.delete()

        messages.success(
            request,
            f"{nb} zone(s) supprimée(s).",
        )

        return redirect("environnement_bo:liste")

    return render(
        request,
        TEMPLATE_DIR + "confirm_delete.html",
        _contexte(
            "Supprimer des zones",
            zones=zones,
            multiple=True,
        ),
    )


# ---------------------------------------------------------------------------
# G. Statistiques environnementales
# ---------------------------------------------------------------------------

@admin_requis
def bo_statistiques(request):
    form = StatistiquesEnvironnementForm(request.GET or None)
    valide = form.is_valid()
    filtres = form.cleaned_data if valide else {}
    stats, graphiques = calculer_statistiques_environnement(filtres)

    return render(
        request,
        TEMPLATE_DIR + "statistiques.html",
        _contexte(
            "Statistiques environnementales",
            form=form,
            stats=stats,
            graphiques=graphiques,
            filtres_invalides=form.is_bound and not valide,
        ),
    )


# ---------------------------------------------------------------------------
# H. Export CSV
# Toutes les lignes correspondant aux filtres actifs, sans pagination.
# ---------------------------------------------------------------------------

@admin_requis
def bo_export_csv(request):
    form, donnees = _filtres(request)

    # Ne pas exporter toutes les données si les critères sont invalides.
    if form.is_bound and not form.is_valid():
        messages.error(
            request,
            "Certains critères de recherche sont invalides. "
            "Veuillez les corriger avant l'export.",
        )
        return redirect("environnement_bo:liste")

    # Le service applique exactement les mêmes filtres et le même tri
    # que la liste du Backoffice.
    zones = filtrer_environnements(donnees)

    tampon = io.StringIO()

    writer = csv.writer(
        tampon,
        delimiter=";",
        lineterminator="\r\n",
    )

    writer.writerow([
        "ID",
        "Nom de la zone",
        "Type de végétation",
        "Surface (ha)",
        "Latitude",
        "Longitude",
        "Température (°C)",
        "Humidité (%)",
        "Précipitations (mm)",
        "Vitesse vent (km/h)",
        "Niveau floraison",
        "Date mesure",
        "Niveau risque",
        "Score qualité",
    ])

    # Pas de pagination : export de tous les résultats filtrés.
    for z in zones.iterator():
        writer.writerow([
            z.idZone,
            z.nomZone,
            z.get_typeVegetation_display(),
            z.surface,
            z.latitude,
            z.longitude,
            z.temperature,
            z.humidite,
            z.precipitation,
            z.vitesseVent,
            z.get_niveauFloraison_display(),
            (
                timezone.localtime(z.dateMesure).strftime("%d/%m/%Y %H:%M")
                if z.dateMesure
                else ""
            ),
            z.get_niveauRisque_display(),
            "" if z.scoreQualite is None else z.scoreQualite,
        ])

    nom = f"environnements_{timezone.localdate():%Y%m%d}.csv"

    response = HttpResponse(
        tampon.getvalue().encode("utf-8-sig"),
        content_type="text/csv; charset=utf-8",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{nom}"'
    )

    return response
