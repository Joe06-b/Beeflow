"""
Vues du BACK OFFICE (administration) du Suivi sanitaire.
Toutes protégées par @admin_requis (statique pour l'instant, voir decorators.py).
"""
import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import admin_requis
from .forms import RechercheSuiviForm, SuiviSanitaireForm
from .models import SuiviSanitaire
from .services import avec_remplace, calculer_statistiques, filtrer_suivis

TEMPLATE_DIR = "backoffice/suivi_sanitaire/"
PAR_PAGE = 10


def _contexte(page_title, **extra):
    """Variables attendues par base_backoffice.html (titre + élément actif de la sidebar)."""
    return {"page_title": page_title, "active_page": "sanitaire", **extra}


def _filtres(request):
    form = RechercheSuiviForm(request.GET or None)
    donnees = form.cleaned_data if form.is_valid() else {}
    return (form if form.is_bound else RechercheSuiviForm()), donnees


# ---------------------------------------------------------------------------
# Liste de gestion : recherche, filtres, tri, pagination, suppression multiple
# ---------------------------------------------------------------------------
@admin_requis
def bo_liste(request):
    form, donnees = _filtres(request)
    suivis = avec_remplace(filtrer_suivis(donnees))

    page = Paginator(suivis, PAR_PAGE).get_page(request.GET.get("page"))

    # Conserver les filtres dans les liens de pagination
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, TEMPLATE_DIR + "liste.html", _contexte(
        "Suivis sanitaires",
        form=form,
        page=page,
        nb_resultats=suivis.count(),
        params=params.urlencode(),
    ))


# ---------------------------------------------------------------------------
# Ajouter / Modifier
# ---------------------------------------------------------------------------
@admin_requis
def bo_ajouter(request):
    form = SuiviSanitaireForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            suivi = form.save()
            messages.success(request, f"Suivi #{suivi.id_suivi} ajouté.", extra_tags="son-ajout")
            if "enregistrer_et_ajouter" in request.POST:
                return redirect("suivi_sanitaire_bo:ajouter")
            return redirect("suivi_sanitaire_bo:liste")
        messages.error(request, "Le formulaire contient des erreurs.", extra_tags="son-erreur")
    return render(request, TEMPLATE_DIR + "form.html", _contexte("Ajouter un suivi", form=form, mode="ajout"))


@admin_requis
def bo_modifier(request, pk):
    suivi = get_object_or_404(SuiviSanitaire, pk=pk)
    form = SuiviSanitaireForm(request.POST or None, instance=suivi)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f"Suivi #{suivi.id_suivi} modifié.", extra_tags="son-modification")
            return redirect("suivi_sanitaire_bo:liste")
        messages.error(request, "Le formulaire contient des erreurs.", extra_tags="son-erreur")
    return render(request, TEMPLATE_DIR + "form.html", _contexte(
        f"Modifier le suivi #{suivi.id_suivi}", form=form, suivi=suivi, mode="modification",
    ))


# ---------------------------------------------------------------------------
# Supprimer (un seul) / Supprimer plusieurs
# ---------------------------------------------------------------------------
@admin_requis
def bo_supprimer(request, pk):
    suivi = get_object_or_404(SuiviSanitaire, pk=pk)
    if request.method == "POST":
        numero = suivi.id_suivi
        suivi.delete()
        messages.success(request, f"Suivi #{numero} supprimé.", extra_tags="son-suppression")
        return redirect("suivi_sanitaire_bo:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", _contexte("Supprimer un suivi", suivis=[suivi]))


@admin_requis
@require_POST
def bo_supprimer_selection(request):
    ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
    if not ids:
        messages.warning(request, "Aucun suivi sélectionné.", extra_tags="son-erreur")
        return redirect("suivi_sanitaire_bo:liste")

    suivis = SuiviSanitaire.objects.filter(pk__in=ids)

    if "confirmer" in request.POST:          # 2e étape : suppression réelle
        nb, _ = suivis.delete()
        messages.success(request, f"{nb} suivi(s) supprimé(s).", extra_tags="son-suppression")
        return redirect("suivi_sanitaire_bo:liste")

    # 1re étape : page de confirmation
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html",
                  _contexte("Supprimer des suivis", suivis=suivis, multiple=True))


# ---------------------------------------------------------------------------
# calculerStatistiques()
# ---------------------------------------------------------------------------
@admin_requis
def bo_statistiques(request):
    stats = calculer_statistiques()
    graphiques = {
        "etat": {"labels": [e["label"] for e in stats["par_etat"]], "data": [e["nb"] for e in stats["par_etat"]]},
        "risque": {"labels": [r["label"] for r in stats["par_risque"]], "data": [r["nb"] for r in stats["par_risque"]]},
        "evolution": {
            "labels": [m["mois"] for m in stats["evolution"]],
            "nb": [m["nb"] for m in stats["evolution"]],
            "critiques": [m["critiques"] for m in stats["evolution"]],
        },
        "ruches": {"labels": [r["code"] for r in stats["par_ruche"]], "data": [r["nb"] for r in stats["par_ruche"]]},
    }
    return render(request, TEMPLATE_DIR + "statistiques.html",
                  _contexte("Statistiques sanitaires", stats=stats, graphiques=graphiques))


# ---------------------------------------------------------------------------
# Export CSV (respecte les filtres de la liste)
# ---------------------------------------------------------------------------
@admin_requis
def bo_export_csv(request):
    _, donnees = _filtres(request)
    suivis = filtrer_suivis(donnees)

    nom = f"suivis_sanitaires_{timezone.localdate():%Y%m%d}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{nom}"'
    response.write("\ufeff")                 # BOM : accents corrects dans Excel

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["ID", "Ruche", "Date suivi", "État", "Maladie", "Symptômes", "Observation",
                     "Traitement", "Dose", "Date traitement", "Prochain contrôle", "Risque"])
    for s in suivis:
        writer.writerow([
            s.id_suivi, s.get_id_ruche_display(), s.date_suivi, s.get_etat_sante_display(),
            s.maladie_detectee, s.symptomes, s.observation, s.type_traitement, s.dose,
            s.date_traitement or "", s.date_prochain_controle or "", s.get_niveau_risque_display(),
        ])
    return response