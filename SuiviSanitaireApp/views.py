from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RechercheSuiviForm, SuiviSanitaireForm
from django.http import Http404

from .maladies import CATEGORIES, MALADIES, anatomie_pour, evolution_pour, fiche_par_slug, maladies_avec_detections, trouver_maladie
from .models import EtatSante, NiveauRisque, SuiviSanitaire
from .services import avec_remplace, compter_alertes, derniers_suivis

TEMPLATE_DIR = "frontoffice/suivi_sanitaire/"

# Rang numérique pour trier les énumérations dans un ordre logique
# (sinon le tri alphabétique donnerait : Eleve, Faible, Moyen)
RANG_ETAT = Case(
    When(etat_sante=EtatSante.BON, then=Value(1)),
    When(etat_sante=EtatSante.MOYEN, then=Value(2)),
    When(etat_sante=EtatSante.CRITIQUE, then=Value(3)),
    output_field=IntegerField(),
)
RANG_RISQUE = Case(
    When(niveau_risque=NiveauRisque.FAIBLE, then=Value(1)),
    When(niveau_risque=NiveauRisque.MOYEN, then=Value(2)),
    When(niveau_risque=NiveauRisque.ELEVE, then=Value(3)),
    output_field=IntegerField(),
)

TRIS = {
    "date_desc": ["-date_suivi", "-id_suivi"],
    "date_asc": ["date_suivi", "id_suivi"],
    "ruche": ["ruche__code_ruche", "-date_suivi"],
    "etat": ["-rang_etat", "-date_suivi"],
    "risque": ["-rang_risque", "-date_suivi"],
    "controle": ["date_prochain_controle", "-date_suivi"],
}


# ---------------------------------------------------------------------------
# consulterSuivi + rechercherSuivi + trierSuivis
# ---------------------------------------------------------------------------
def liste_suivis(request):
    form = RechercheSuiviForm(request.GET or None)
    suivis = SuiviSanitaire.objects.select_related("ruche").annotate(rang_etat=RANG_ETAT, rang_risque=RANG_RISQUE)
    tri = "date_desc"

    if form.is_valid():
        q = form.cleaned_data.get("q", "").strip()
        ruche = form.cleaned_data.get("ruche")
        etat = form.cleaned_data.get("etat_sante")
        risque = form.cleaned_data.get("niveau_risque")
        tri = form.cleaned_data.get("tri") or "date_desc"

        if q:
            filtre = (
                Q(maladie_detectee__icontains=q)
                | Q(symptomes__icontains=q)
                | Q(observation__icontains=q)
                | Q(type_traitement__icontains=q)
                | Q(ruche__code_ruche__icontains=q)      # recherche par code de ruche (ex : "R-002")
            )
            # Recherche par numéro de suivi
            if q.isdigit():
                filtre |= Q(id_suivi=int(q))
            suivis = suivis.filter(filtre)

        if ruche:
            suivis = suivis.filter(ruche=ruche)
        if etat:
            suivis = suivis.filter(etat_sante=etat)
        if risque:
            suivis = suivis.filter(niveau_risque=risque)

    suivis = avec_remplace(suivis.order_by(*TRIS[tri]))

    tous = SuiviSanitaire.objects.all()
    alertes = compter_alertes()
    context = {
        "form": form if form.is_bound else RechercheSuiviForm(),
        "suivis": suivis,
        "nb_resultats": suivis.count(),
        "nb_total": tous.count(),
        "nb_critiques": alertes["critiques"],          # dernier suivi de chaque ruche
        "nb_retard": alertes["en_retard"],
    }
    return render(request, TEMPLATE_DIR + "liste.html", context)


# ---------------------------------------------------------------------------
# consulterSuivi (détail)
# ---------------------------------------------------------------------------
def detail_suivi(request, pk):
    suivi = get_object_or_404(SuiviSanitaire.objects.select_related("ruche"), pk=pk)
    historique = (
        SuiviSanitaire.objects.filter(ruche_id=suivi.ruche_id)
        .exclude(pk=suivi.pk)
        .order_by("-date_suivi")[:5]
    )
    return render(request, TEMPLATE_DIR + "detail.html", {
        "suivi": suivi,
        "historique": historique,
        "maladie": trouver_maladie(suivi.maladie_detectee),     # fiche de l'atlas, si la maladie est connue
    })


# ---------------------------------------------------------------------------
# ajouterSuivi
# ---------------------------------------------------------------------------
def ajouter_suivi(request):
    if request.method == "POST":
        form = SuiviSanitaireForm(request.POST)
        if form.is_valid():
            suivi = form.save()
            messages.success(request, f"Le suivi #{suivi.id_suivi} a été ajouté avec succès.", extra_tags="son-ajout")
            return redirect("suivi_sanitaire:detail", pk=suivi.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.", extra_tags="son-erreur")
    else:
        initial = {}
        ruche = request.GET.get("ruche")          # ex : /suivis/ajouter/?ruche=2
        if ruche and ruche.isdigit():
            initial["ruche"] = int(ruche)
        form = SuiviSanitaireForm(initial=initial)

    return render(request, TEMPLATE_DIR + "form.html", {"form": form, "titre": "Ajouter un suivi sanitaire", "mode": "ajout"})


# ---------------------------------------------------------------------------
# modifierSuivi
# ---------------------------------------------------------------------------
def modifier_suivi(request, pk):
    suivi = get_object_or_404(SuiviSanitaire, pk=pk)
    if request.method == "POST":
        form = SuiviSanitaireForm(request.POST, instance=suivi)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le suivi #{suivi.id_suivi} a été modifié avec succès.", extra_tags="son-modification")
            return redirect("suivi_sanitaire:detail", pk=suivi.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.", extra_tags="son-erreur")
    else:
        form = SuiviSanitaireForm(instance=suivi)

    return render(request, TEMPLATE_DIR + "form.html", {"form": form, "suivi": suivi, "titre": f"Modifier le suivi #{suivi.id_suivi}", "mode": "modification"})


# ---------------------------------------------------------------------------
# supprimerSuivi (GET = page de confirmation, POST = suppression)
# ---------------------------------------------------------------------------
def supprimer_suivi(request, pk):
    suivi = get_object_or_404(SuiviSanitaire, pk=pk)
    if request.method == "POST":
        numero = suivi.id_suivi
        suivi.delete()
        messages.success(request, f"Le suivi #{numero} a été supprimé.", extra_tags="son-suppression")
        return redirect("suivi_sanitaire:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", {"suivi": suivi})


# ---------------------------------------------------------------------------
# consulterAlertes
# ---------------------------------------------------------------------------
def alertes_suivis(request):
    aujourd_hui = date.today()
    dans_7_jours = aujourd_hui + timedelta(days=7)

    # Seul le DERNIER suivi de chaque ruche compte : si la ruche a été revisitée,
    # l'ancien contrôle est fait et l'ancien état critique a été réévalué.
    actuels = derniers_suivis()
    critiques = actuels.filter(
        Q(etat_sante=EtatSante.CRITIQUE) | Q(niveau_risque=NiveauRisque.ELEVE)
    ).order_by("-date_suivi")
    en_retard = actuels.filter(
        date_prochain_controle__lt=aujourd_hui
    ).order_by("date_prochain_controle")
    proches = actuels.filter(
        date_prochain_controle__range=(aujourd_hui, dans_7_jours)
    ).order_by("date_prochain_controle")

    context = {
        "critiques": critiques,
        "en_retard": en_retard,
        "proches": proches,
        "aujourd_hui": aujourd_hui,
    }
    return render(request, TEMPLATE_DIR + "alertes.html", context)


# ---------------------------------------------------------------------------
# Notification sonore : nombre d'alertes au format JSON (appelé en JavaScript)
# ---------------------------------------------------------------------------
JOURS_ALERTE = 7   # un contrôle est "proche" s'il tombe dans les 7 prochains jours


def alertes_compte(request):
    compte = compter_alertes(JOURS_ALERTE)
    return JsonResponse({
        "en_retard": compte["en_retard"],
        "proches": compte["proches"],
        "aujourdhui": compte["aujourdhui"],
        "jours": JOURS_ALERTE,
    })



# ---------------------------------------------------------------------------
# Atlas des maladies (affichage uniquement, aucune donnée enregistrée)
# ---------------------------------------------------------------------------
def atlas_maladies(request):
    textes = SuiviSanitaire.objects.exclude(maladie_detectee="").values_list("maladie_detectee", flat=True)
    fiches = maladies_avec_detections(textes)
    detectees = [f for f in fiches if f["detections"]]
    plus_frequente = max(detectees, key=lambda f: f["detections"]) if detectees else None
    return render(request, TEMPLATE_DIR + "atlas.html", {
        "fiches": sorted(fiches, key=lambda f: -f["gravite"]),
        "categories": CATEGORIES,
        "nb_detectees": len(detectees),
        "nb_a_signaler": sum(1 for f in fiches if f["a_signaler"]),
        "plus_frequente": plus_frequente,
    })



# ---------------------------------------------------------------------------
# Explorer une maladie en 3D (affichage uniquement)
# ---------------------------------------------------------------------------
def maladie_3d(request, slug):
    fiche = fiche_par_slug(slug)
    if not fiche:
        raise Http404("Maladie inconnue")
    return render(request, TEMPLATE_DIR + "maladie_3d.html", {
        "m": fiche,
        "anatomie": anatomie_pour(slug),
        "autres": [{"slug": x["slug"], "nom": x["nom"]} for x in MALADIES],
    })


def maladie_evolution(request, slug):
    """Évolution d'une maladie dans la ruche, semaine par semaine, avec ou sans traitement (affichage uniquement)."""
    fiche = fiche_par_slug(slug)
    evolution = evolution_pour(slug)
    if not fiche or not evolution:
        raise Http404("Maladie inconnue")
    return render(request, TEMPLATE_DIR + "maladie_evolution.html", {
        "m": fiche,
        "evolution": evolution,
        "autres": [{"slug": x["slug"], "nom": x["nom"]} for x in MALADIES],
    })
