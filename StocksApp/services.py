"""
Logique métier du module Stock (indépendante des vues, utilisée par le front ET le back) :
  - filtrer_stocks()          -> rechercherStock() + trierStocks()
  - calculer_statistiques()   -> tableau de bord / consulter alertes
"""
from decimal import Decimal

from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When

from .models import Stock

Statut = Stock.Statut
STATUTS_ALERTE = [Statut.VIDE, Statut.ALERTE_BASSE, Statut.ALERTE_HAUTE, Statut.PLEIN]

# ---------------------------------------------------------------------------
# Tri logique des statuts (les plus urgents d'abord)
# ---------------------------------------------------------------------------
RANG_STATUT = Case(
    When(statut=Statut.VIDE, then=Value(1)),
    When(statut=Statut.ALERTE_BASSE, then=Value(2)),
    When(statut=Statut.PLEIN, then=Value(3)),
    When(statut=Statut.ALERTE_HAUTE, then=Value(4)),
    When(statut=Statut.NORMAL, then=Value(5)),
    output_field=IntegerField(),
)
TRIS = {
    "nom": ["nom_stock"],
    "recent": ["-date_creation"],
    "alerte": ["rang_statut", "nom_stock"],
    "remplissage_desc": ["-taux_remplissage", "nom_stock"],
    "remplissage_asc": ["taux_remplissage", "nom_stock"],
    "quantite": ["-quantite_actuelle", "nom_stock"],
}


def filtrer_stocks(donnees):
    """donnees = cleaned_data d'un RechercheStockForm (ou {})."""
    stocks = Stock.objects.annotate(rang_statut=RANG_STATUT).prefetch_related("responsables")

    q = (donnees.get("q") or "").strip()
    if q:
        stocks = stocks.filter(
            Q(nom_stock__icontains=q)
            | Q(emplacement__icontains=q)
            | Q(description__icontains=q)
        )
    if donnees.get("type_stock"):
        stocks = stocks.filter(type_stock=donnees["type_stock"])
    if donnees.get("statut"):
        stocks = stocks.filter(statut=donnees["statut"])

    return stocks.order_by(*TRIS.get(donnees.get("tri") or "nom", TRIS["nom"]))


# ---------------------------------------------------------------------------
# calculerStatistiques()
# ---------------------------------------------------------------------------
def _repartition(champ, choices):
    """Nombre de stocks par valeur d'une énumération, dans l'ordre de l'énumération."""
    comptes = dict(Stock.objects.order_by().values_list(champ).annotate(n=Count("id")))
    return [{"valeur": v, "label": l, "nb": comptes.get(v, 0)} for v, l in choices]


def calculer_statistiques():
    tous = Stock.objects.all()
    sommes = tous.aggregate(capacite=Sum("capacite_max"), quantite=Sum("quantite_actuelle"))
    capacite = sommes["capacite"] or Decimal("0")
    quantite = sommes["quantite"] or Decimal("0")

    return {
        "total": tous.count(),
        "nb_alertes": tous.filter(statut__in=STATUTS_ALERTE).count(),
        "nb_normaux": tous.filter(statut=Statut.NORMAL).count(),
        "capacite_totale": capacite,
        "quantite_totale": quantite,
        "taux_global": round(quantite * 100 / capacite, 1) if capacite else 0,
        "par_statut": _repartition("statut", Statut.choices),
        "par_type": _repartition("type_stock", Stock.TypeStock.choices),
    }