from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RechercheSuiviForm, SuiviSanitaireForm
from .models import EtatSante, NiveauRisque, RUCHES_TEST, SuiviSanitaire

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
    "ruche": ["id_ruche", "-date_suivi"],
    "etat": ["-rang_etat", "-date_suivi"],
    "risque": ["-rang_risque", "-date_suivi"],
    "controle": ["date_prochain_controle", "-date_suivi"],
}


# ---------------------------------------------------------------------------
# consulterSuivi + rechercherSuivi + trierSuivis
# ---------------------------------------------------------------------------
def liste_suivis(request):
    form = RechercheSuiviForm(request.GET or None)
    suivis = SuiviSanitaire.objects.annotate(rang_etat=RANG_ETAT, rang_risque=RANG_RISQUE)
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
            )
            # Recherche par code de ruche (ex : "R-002")
            ids_ruches = [rid for rid, code in RUCHES_TEST if q.lower() in code.lower()]
            if ids_ruches:
                filtre |= Q(id_ruche__in=ids_ruches)
            # Recherche par numéro de suivi
            if q.isdigit():
                filtre |= Q(id_suivi=int(q))
            suivis = suivis.filter(filtre)

        if ruche:
            suivis = suivis.filter(id_ruche=ruche)
        if etat:
            suivis = suivis.filter(etat_sante=etat)
        if risque:
            suivis = suivis.filter(niveau_risque=risque)

    suivis = suivis.order_by(*TRIS[tri])

    tous = SuiviSanitaire.objects.all()
    context = {
        "form": form if form.is_bound else RechercheSuiviForm(),
        "suivis": suivis,
        "nb_resultats": suivis.count(),
        "nb_total": tous.count(),
        "nb_critiques": tous.filter(Q(etat_sante=EtatSante.CRITIQUE) | Q(niveau_risque=NiveauRisque.ELEVE)).count(),
        "nb_retard": tous.filter(date_prochain_controle__lt=date.today()).count(),
    }
    return render(request, TEMPLATE_DIR + "liste.html", context)


# ---------------------------------------------------------------------------
# consulterSuivi (détail)
# ---------------------------------------------------------------------------
def detail_suivi(request, pk):
    suivi = get_object_or_404(SuiviSanitaire, pk=pk)
    historique = (
        SuiviSanitaire.objects.filter(id_ruche=suivi.id_ruche)
        .exclude(pk=suivi.pk)
        .order_by("-date_suivi")[:5]
    )
    return render(request, TEMPLATE_DIR + "detail.html", {"suivi": suivi, "historique": historique})


# ---------------------------------------------------------------------------
# ajouterSuivi
# ---------------------------------------------------------------------------
def ajouter_suivi(request):
    if request.method == "POST":
        form = SuiviSanitaireForm(request.POST)
        if form.is_valid():
            suivi = form.save()
            messages.success(request, f"Le suivi #{suivi.id_suivi} a été ajouté avec succès.")
            return redirect("suivi_sanitaire:detail", pk=suivi.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.")
    else:
        initial = {}
        ruche = request.GET.get("ruche")          # ex : /suivis/ajouter/?ruche=2
        if ruche and ruche.isdigit():
            initial["id_ruche"] = int(ruche)
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
            messages.success(request, f"Le suivi #{suivi.id_suivi} a été modifié avec succès.")
            return redirect("suivi_sanitaire:detail", pk=suivi.pk)
        messages.error(request, "Le formulaire contient des erreurs. Veuillez les corriger.")
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
        messages.success(request, f"Le suivi #{numero} a été supprimé.")
        return redirect("suivi_sanitaire:liste")
    return render(request, TEMPLATE_DIR + "confirmer_suppression.html", {"suivi": suivi})


# ---------------------------------------------------------------------------
# consulterAlertes
# ---------------------------------------------------------------------------
def alertes_suivis(request):
    aujourd_hui = date.today()
    dans_7_jours = aujourd_hui + timedelta(days=7)

    critiques = SuiviSanitaire.objects.filter(
        Q(etat_sante=EtatSante.CRITIQUE) | Q(niveau_risque=NiveauRisque.ELEVE)
    ).order_by("-date_suivi")
    en_retard = SuiviSanitaire.objects.filter(
        date_prochain_controle__lt=aujourd_hui
    ).order_by("date_prochain_controle")
    proches = SuiviSanitaire.objects.filter(
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
    aujourd_hui = date.today()
    en_retard = SuiviSanitaire.objects.filter(date_prochain_controle__lt=aujourd_hui)
    proches = SuiviSanitaire.objects.filter(
        date_prochain_controle__range=(aujourd_hui, aujourd_hui + timedelta(days=JOURS_ALERTE))
    )
    aujourdhui = proches.filter(date_prochain_controle=aujourd_hui).count()
    return JsonResponse({
        "en_retard": en_retard.count(),
        "proches": proches.count(),
        "aujourdhui": aujourdhui,
        "jours": JOURS_ALERTE,
    })
