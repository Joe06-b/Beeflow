"""
Logique métier du Suivi sanitaire (indépendante des vues) :
  - filtrer_suivis()          -> rechercherSuivi() + trierSuivis()
  - calculer_statistiques()   -> calculerStatistiques()
"""
from datetime import date, timedelta

from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Value, When
from django.db.models.functions import Lower, TruncMonth

from .models import EtatSante, NiveauRisque, RUCHES_TEST, SuiviSanitaire

# ---------------------------------------------------------------------------
# Tri logique des énumérations (sinon tri alphabétique : Eleve, Faible, Moyen)
# ---------------------------------------------------------------------------
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
CODES_RUCHES = dict(RUCHES_TEST)


def filtrer_suivis(donnees):
    """donnees = cleaned_data d'un RechercheSuiviForm (ou {})."""
    suivis = SuiviSanitaire.objects.annotate(rang_etat=RANG_ETAT, rang_risque=RANG_RISQUE)

    q = (donnees.get("q") or "").strip()
    if q:
        filtre = (
            Q(maladie_detectee__icontains=q)
            | Q(symptomes__icontains=q)
            | Q(observation__icontains=q)
            | Q(type_traitement__icontains=q)
        )
        ids = [rid for rid, code in RUCHES_TEST if q.lower() in code.lower()]
        if ids:
            filtre |= Q(id_ruche__in=ids)
        if q.isdigit():
            filtre |= Q(id_suivi=int(q))
        suivis = suivis.filter(filtre)

    if donnees.get("ruche"):
        suivis = suivis.filter(id_ruche=donnees["ruche"])
    if donnees.get("etat_sante"):
        suivis = suivis.filter(etat_sante=donnees["etat_sante"])
    if donnees.get("niveau_risque"):
        suivis = suivis.filter(niveau_risque=donnees["niveau_risque"])

    return suivis.order_by(*TRIS[donnees.get("tri") or "date_desc"])


# ---------------------------------------------------------------------------
# calculerStatistiques()
# ---------------------------------------------------------------------------
def _repartition(champ, choices):
    """Nombre de suivis par valeur d'une énumération, dans l'ordre de l'énumération."""
    comptes = dict(SuiviSanitaire.objects.order_by().values_list(champ).annotate(n=Count("id_suivi")))
    return [{"valeur": v, "label": l, "nb": comptes.get(v, 0)} for v, l in choices]


def _pourcentage(partie, total):
    return round(partie * 100 / total, 1) if total else 0


def avec_remplace(qs):
    """Ajoute à chaque suivi « remplace » = un suivi plus récent existe pour la même ruche
    (une seule requête SQL, au lieu d'une par ligne de tableau)."""
    plus_recent = SuiviSanitaire.objects.filter(id_ruche=OuterRef("id_ruche")).filter(
        Q(date_suivi__gt=OuterRef("date_suivi"))
        | Q(date_suivi=OuterRef("date_suivi"), id_suivi__gt=OuterRef("id_suivi"))
    )
    return qs.annotate(remplace=Exists(plus_recent))


def derniers_suivis(qs=None):
    """Garde uniquement le DERNIER suivi de chaque ruche (le plus récent).
    Les alertes (contrôle en retard, contrôle proche, état critique) ne concernent que lui :
    si une ruche a été revisitée, le contrôle prévu par l'ancien suivi est considéré comme fait."""
    qs = SuiviSanitaire.objects.all() if qs is None else qs
    return avec_remplace(qs).filter(remplace=False)


def compter_alertes(jours=7):
    """Nombre de contrôles en retard / proches, sur le dernier suivi de chaque ruche."""
    aujourd_hui = date.today()
    actuels = derniers_suivis()
    return {
        "en_retard": actuels.filter(date_prochain_controle__lt=aujourd_hui).count(),
        "proches": actuels.filter(date_prochain_controle__range=(aujourd_hui, aujourd_hui + timedelta(days=jours))).count(),
        "aujourdhui": actuels.filter(date_prochain_controle=aujourd_hui).count(),
        "critiques": actuels.filter(Q(etat_sante=EtatSante.CRITIQUE) | Q(niveau_risque=NiveauRisque.ELEVE)).count(),
    }


def calculer_statistiques():
    aujourd_hui = date.today()
    tous = SuiviSanitaire.objects.all()
    total = tous.count()

    nb_critiques = tous.filter(Q(etat_sante=EtatSante.CRITIQUE) | Q(niveau_risque=NiveauRisque.ELEVE)).count()
    alertes = compter_alertes(7)                      # dernier suivi de chaque ruche uniquement
    nb_retard = alertes["en_retard"]
    nb_proches = alertes["proches"]
    nb_traites = tous.exclude(type_traitement="").count()
    nb_malades = tous.exclude(maladie_detectee="").count()
    nb_ruches_suivies = tous.order_by().values("id_ruche").distinct().count()

    # Évolution sur les 12 derniers mois
    debut = (aujourd_hui.replace(day=1) - timedelta(days=335)).replace(day=1)
    par_mois = {
        ligne["mois"].strftime("%Y-%m"): ligne
        for ligne in tous.filter(date_suivi__gte=debut).order_by()
        .annotate(mois=TruncMonth("date_suivi"))
        .values("mois")
        .annotate(
            nb=Count("id_suivi"),
            critiques=Count("id_suivi", filter=Q(etat_sante=EtatSante.CRITIQUE)),
        )
    }
    evolution = []
    mois = debut
    for _ in range(12):
        cle = mois.strftime("%Y-%m")
        ligne = par_mois.get(cle, {})
        evolution.append({"mois": mois.strftime("%m/%Y"), "nb": ligne.get("nb", 0), "critiques": ligne.get("critiques", 0)})
        mois = (mois.replace(day=28) + timedelta(days=4)).replace(day=1)   # mois suivant

    # Par ruche
    par_ruche = []
    lignes = {
        l["id_ruche"]: l
        for l in tous.order_by().values("id_ruche").annotate(
            nb=Count("id_suivi"),
            critiques=Count("id_suivi", filter=Q(etat_sante=EtatSante.CRITIQUE)),
            traitements=Count("id_suivi", filter=~Q(type_traitement="")),
        )
    }
    for rid, code in RUCHES_TEST:
        l = lignes.get(rid, {})
        par_ruche.append({"id_ruche": rid, "code": code, "nb": l.get("nb", 0),
                          "critiques": l.get("critiques", 0), "traitements": l.get("traitements", 0)})

    # Top 5 des maladies et des traitements (insensible à la casse)
    top_maladies = list(
        tous.exclude(maladie_detectee="").annotate(nom=Lower("maladie_detectee"))
        .values("nom").annotate(nb=Count("id_suivi")).order_by("-nb", "nom")[:5]
    )
    top_traitements = list(
        tous.exclude(type_traitement="").annotate(nom=Lower("type_traitement"))
        .values("nom").annotate(nb=Count("id_suivi")).order_by("-nb", "nom")[:5]
    )

    return {
        "total": total,
        "nb_critiques": nb_critiques,
        "nb_retard": nb_retard,
        "nb_proches": nb_proches,
        "nb_ruches_suivies": nb_ruches_suivies,
        "nb_ruches_total": len(RUCHES_TEST),
        "taux_traitement": _pourcentage(nb_traites, total),
        "taux_maladie": _pourcentage(nb_malades, total),
        "taux_critique": _pourcentage(nb_critiques, total),
        "par_etat": _repartition("etat_sante", EtatSante.choices),
        "par_risque": _repartition("niveau_risque", NiveauRisque.choices),
        "evolution": evolution,
        "par_ruche": par_ruche,
        "top_maladies": top_maladies,
        "top_traitements": top_traitements,
    }