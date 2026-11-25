
"""
Logique métier du module Environnement :
- Recherche par nom de zone.
- Filtres principaux : végétation, floraison et risque.
- Filtres avancés : plages numériques et période de mesure.
- Tri dynamique avec ordre logique des énumérations.
"""

from django.db.models import Avg, Case, Count, IntegerField, Q, Sum, Value, When
from django.db.models.functions import TruncDate

from .models import (
    Environnement,
    NiveauFloraison,
    NiveauRisque,
    TypeVegetation,
)


# Ordre logique des niveaux de risque
ORDRE_RISQUE = [
    NiveauRisque.FAIBLE,
    NiveauRisque.MOYEN,
    NiveauRisque.ELEVE,
    NiveauRisque.CRITIQUE,
]


def _ordre_enum(champ, valeurs):
    """
    Construit un ordre personnalisé pour un champ énuméré.

    Exemple :
    Floraison : Absente -> Faible -> Moyenne -> Abondante
    Risque    : Faible -> Moyen -> Élevé -> Critique
    """

    expression = Case(
        *[
            When(**{champ: valeur}, then=Value(index))
            for index, valeur in enumerate(valeurs)
        ],
        default=Value(len(valeurs)),
        output_field=IntegerField(),
    )

    return expression.asc()


# Critères de tri disponibles
TRIS = {
    "date_desc": ["-dateMesure", "-idZone"],
    "date_asc": ["dateMesure", "idZone"],
    "nom_asc": ["nomZone", "idZone"],
    "surface_asc": ["surface", "idZone"],
    "surface_desc": ["-surface", "-idZone"],
}


def filtrer_environnements(donnees=None):
    """
    Retourne les environnements filtrés et triés selon donnees
    (cleaned_data de RechercheEnvironnementForm).

    Recherche :
        q

    Filtres principaux :
        type_vegetation
        niveau_floraison
        niveau_risque

    Filtres avancés :
        surface_min / surface_max
        temperature_min / temperature_max
        humidite_min / humidite_max
        precipitation_min / precipitation_max
        vitesseVent_min / vitesseVent_max
        date_debut / date_fin

    Tri :
        date, nom, surface et ordre logique du risque.
    """

    donnees = donnees or {}

    zones = Environnement.objects.all()

    # --------------------------------------------------
    # 1. RECHERCHE TEXTUELLE
    # --------------------------------------------------

    q = (donnees.get("q") or "").strip()

    if q:
        zones = zones.filter(nomZone__icontains=q)

    # --------------------------------------------------
    # 2. FILTRES PRINCIPAUX
    # --------------------------------------------------

    if donnees.get("type_vegetation"):
        zones = zones.filter(
            typeVegetation=donnees["type_vegetation"]
        )

    if donnees.get("niveau_floraison"):
        zones = zones.filter(
            niveauFloraison=donnees["niveau_floraison"]
        )

    if donnees.get("niveau_risque"):
        zones = zones.filter(
            niveauRisque=donnees["niveau_risque"]
        )

    # --------------------------------------------------
    # 3. FILTRES NUMÉRIQUES AVANCÉS
    # --------------------------------------------------

    filtres_numeriques = {
        "surface": ("surface_min", "surface_max"),
        "temperature": ("temperature_min", "temperature_max"),
        "humidite": ("humidite_min", "humidite_max"),
        "precipitation": (
            "precipitation_min",
            "precipitation_max",
        ),
        "vitesseVent": ("vitesseVent_min", "vitesseVent_max"),
    }

    for champ, (cle_min, cle_max) in filtres_numeriques.items():

        minimum = donnees.get(cle_min)
        maximum = donnees.get(cle_max)

        if minimum is not None:
            zones = zones.filter(
                **{f"{champ}__gte": minimum}
            )

        if maximum is not None:
            zones = zones.filter(
                **{f"{champ}__lte": maximum}
            )

    # --------------------------------------------------
    # 4. FILTRE PAR PÉRIODE
    # --------------------------------------------------

    date_debut = donnees.get("date_debut")
    date_fin = donnees.get("date_fin")

    if date_debut:
        zones = zones.filter(
            dateMesure__date__gte=date_debut
        )

    if date_fin:
        zones = zones.filter(
            dateMesure__date__lte=date_fin
        )

    # --------------------------------------------------
    # 5. TRI
    # --------------------------------------------------

    tri = donnees.get("tri") or "date_desc"

    if tri == "risque_asc":
        zones = zones.order_by(
            _ordre_enum("niveauRisque", ORDRE_RISQUE),
            "-dateMesure",
            "-idZone",
        )

    else:
        ordre = TRIS.get(tri, TRIS["date_desc"])
        zones = zones.order_by(*ordre)

    return zones


def _repartition_statistique(zones, champ, choix):
    """Retourne les effectifs dans l'ordre métier des choix du modèle."""
    comptes = dict(
        zones.order_by()
        .values(champ)
        .annotate(nombre=Count("idZone"))
        .values_list(champ, "nombre")
    )
    repartition = [
        {"label": libelle, "nombre": comptes.get(valeur, 0)}
        for valeur, libelle in choix
    ]
    non_renseigne = comptes.get("", 0) + comptes.get(None, 0)
    if non_renseigne:
        repartition.append({"label": "Non renseigné", "nombre": non_renseigne})
    return repartition


def calculer_statistiques_environnement(filtres=None):
    """Calcule les KPI et les séries graphiques à partir des zones filtrées."""
    filtres = filtres or {}
    zones = Environnement.objects.all()

    for cle, champ in (
        ("type_vegetation", "typeVegetation"),
        ("niveau_floraison", "niveauFloraison"),
        ("niveau_risque", "niveauRisque"),
    ):
        if filtres.get(cle):
            zones = zones.filter(**{champ: filtres[cle]})

    if filtres.get("date_debut"):
        zones = zones.filter(dateMesure__date__gte=filtres["date_debut"])
    if filtres.get("date_fin"):
        zones = zones.filter(dateMesure__date__lte=filtres["date_fin"])

    totaux = zones.aggregate(
        nombre=Count("idZone"),
        surface=Sum("surface"),
        temperature=Avg("temperature"),
        humidite=Avg("humidite"),
        precipitation=Avg("precipitation"),
        types_vegetation=Count(
            "typeVegetation",
            distinct=True,
            filter=~Q(typeVegetation=""),
        ),
    )

    repartitions = {
        "vegetation": _repartition_statistique(
            zones, "typeVegetation", TypeVegetation.choices
        ),
        "floraison": _repartition_statistique(
            zones, "niveauFloraison", NiveauFloraison.choices
        ),
        "risque": _repartition_statistique(
            zones, "niveauRisque", NiveauRisque.choices
        ),
    }

    mesures_par_jour = list(
        zones.order_by()
        .filter(Q(temperature__isnull=False) | Q(humidite__isnull=False))
        .annotate(jour=TruncDate("dateMesure"))
        .values("jour")
        .annotate(
            temperature=Avg("temperature"),
            humidite=Avg("humidite"),
        )
        .order_by("jour")
    )
    jours_temperature = sum(
        ligne["temperature"] is not None for ligne in mesures_par_jour
    )
    jours_humidite = sum(
        ligne["humidite"] is not None for ligne in mesures_par_jour
    )
    evolution_disponible = jours_temperature >= 2 and jours_humidite >= 2

    statistiques = {
        "total": totaux["nombre"] or 0,
        "surface_totale": (
            round(totaux["surface"], 2) if totaux["surface"] is not None else None
        ),
        "temperature_moyenne": (
            round(totaux["temperature"], 1)
            if totaux["temperature"] is not None
            else None
        ),
        "humidite_moyenne": (
            round(totaux["humidite"], 1)
            if totaux["humidite"] is not None
            else None
        ),
        "precipitation_moyenne": (
            round(totaux["precipitation"], 1)
            if totaux["precipitation"] is not None
            else None
        ),
        "types_vegetation": totaux["types_vegetation"] or 0,
    }
    graphiques = {
        cle: {
            "labels": [ligne["label"] for ligne in lignes],
            "data": [ligne["nombre"] for ligne in lignes],
        }
        for cle, lignes in repartitions.items()
    }
    graphiques["evolution"] = {
        "disponible": evolution_disponible,
        "labels": [ligne["jour"].strftime("%d/%m/%Y") for ligne in mesures_par_jour],
        "temperature": [ligne["temperature"] for ligne in mesures_par_jour],
        "humidite": [ligne["humidite"] for ligne in mesures_par_jour],
    }

    return statistiques, graphiques
