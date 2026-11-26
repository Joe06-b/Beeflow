from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# ---------------------------------------------------------------------------
# Association « Stocker » avec le module Produits : Stock 1 — 0..* Produit
# C'est le modèle Produit (ProduitApp) qui porte la clé étrangère :
#     stock = models.ForeignKey("StocksApp.Stock", on_delete=models.PROTECT, related_name="produits")
# La place occupée par un produit = son volume de stockage, en m³.
# Les noms ci-dessous doivent correspondre au modèle Produit de ProduitApp.
# ---------------------------------------------------------------------------
PRODUIT_RELATED_NAME = "produits"           # related_name de la clé étrangère Produit.stock
PRODUIT_CHAMP_VOLUME = "volume_stockage"    # volume du produit, en m³ (pour toute sa quantité)

UNITE = "m³"


def volume_de(produit):
    """Volume (m³) occupé par un produit, en Decimal (0 si non renseigné)."""
    valeur = getattr(produit, PRODUIT_CHAMP_VOLUME, None)
    return Decimal(str(valeur)) if valeur not in (None, "") else Decimal("0")


def formater(nombre):
    """1.50000 -> '1,5' ; 2.000 -> '2' ; 0.03500 -> '0,035' (affichage)."""
    texte = f"{Decimal(nombre):.5f}".rstrip("0").rstrip(".")
    return texte.replace(".", ",")


class Stock(models.Model):

    class TypeStock(models.TextChoices):
        MIEL = "MIEL", "Miel"
        CIRE = "CIRE", "Cire"
        POLLEN = "POLLEN", "Pollen"
        PROPOLIS = "PROPOLIS", "Propolis"
        GELEE_ROYALE = "GELEE_ROYALE", "Gelée royale"

    class Statut(models.TextChoices):
        VIDE = "VIDE", "Vide"
        ALERTE_BASSE = "ALERTE_BASSE", "Alerte basse"
        NORMAL = "NORMAL", "Normal"
        ALERTE_HAUTE = "ALERTE_HAUTE", "Alerte haute"
        PLEIN = "PLEIN", "Plein"

    # --- Attributs du diagramme de classes ---
    nom_stock = models.CharField("Nom du stock", max_length=100, unique=True)
    type_stock = models.CharField(
        "Type de stock", max_length=20,
        choices=TypeStock.choices, default=TypeStock.MIEL,
    )
    emplacement = models.CharField("Emplacement", max_length=150)
    description = models.TextField("Description", blank=True)

    # Volumes en m³
    capacite_max = models.DecimalField(
        "Capacité maximale (m³)", max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    seuil_alerte_min = models.DecimalField(
        "Seuil d'alerte minimum (m³)", max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    seuil_alerte_max = models.DecimalField(
        "Seuil d'alerte maximum (m³)", max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # Calculés automatiquement à partir des volumes des produits affectés (jamais saisis)
    quantite_actuelle = models.DecimalField(
        "Quantité actuelle (m³)", max_digits=12, decimal_places=5,
        default=0, editable=False,
    )
    taux_remplissage = models.DecimalField(
        "Taux de remplissage (%)", max_digits=5, decimal_places=2,
        default=0, editable=False,
    )
    statut = models.CharField(
        "Statut", max_length=20, choices=Statut.choices,
        default=Statut.VIDE, editable=False,
    )

    # Association « Controler » : Utilisateur 1..* — 0..* Stock
    responsables = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="stocks_controles",
        blank=True,
        verbose_name="Responsables",
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        ordering = ["nom_stock"]

    def __str__(self):
        return f"{self.nom_stock} ({self.get_type_stock_display()})"

    # ------------------------------------------------------------------
    # Produits stockés (association « Stocker »)
    # ------------------------------------------------------------------
    def _produits(self):
        """Produits affectés à ce stock ([] tant que ProduitApp n'a pas la clé étrangère)."""
        if not self.pk:
            return []
        gestionnaire = getattr(self, PRODUIT_RELATED_NAME, None)
        return list(gestionnaire.all()) if gestionnaire is not None else []

    def produits_avec_volumes(self):
        """[{'produit': p, 'volume': Decimal en m³, 'part': % de la capacité}, ...]"""
        lignes = []
        for p in self._produits():
            v = volume_de(p)
            part = (v / self.capacite_max * 100).quantize(Decimal("0.1")) if self.capacite_max else Decimal("0")
            lignes.append({"produit": p, "volume": v, "part": part})
        return lignes

    @property
    def nb_produits(self):
        return len(self._produits())

    def calculer_quantite(self, exclure_pk=None):
        """Somme des volumes (m³) des produits du stock."""
        return sum(
            (volume_de(p) for p in self._produits() if exclure_pk is None or p.pk != exclure_pk),
            Decimal("0"),
        )

    @property
    def espace_libre(self):
        return max(self.capacite_max - self.quantite_actuelle, Decimal("0"))

    def peut_accueillir(self, volume, produit=None):
        """
        Vérifie qu'un produit de ce volume (m³) peut être rangé dans ce stock.
        À appeler depuis Produit.clean() (module Produits).
        Retourne (True, "") ou (False, "message d'erreur").
        """
        if volume is None:
            return False, "Indiquez le volume de stockage du produit (m³)."
        v = Decimal(str(volume))
        exclure = produit.pk if produit is not None and produit.pk else None
        libre = self.capacite_max - self.calculer_quantite(exclure_pk=exclure)
        if v > libre:
            return False, (
                f"Place insuffisante dans « {self.nom_stock} » : "
                f"{formater(libre)} {UNITE} libres, ce produit occupe {formater(v)} {UNITE}."
            )
        return True, ""

    def libelle_affectation(self):
        """Texte de la liste « Stock d'affectation » du formulaire Produit."""
        return f"{self.nom_stock} — {self.get_type_stock_display()} — {formater(self.espace_libre)} {UNITE} libres"

    # ------------------------------------------------------------------
    # Pour l'affichage (couleur du badge et de la jauge)
    # ------------------------------------------------------------------
    @property
    def niveau_alerte(self):
        return {
            self.Statut.VIDE: "bad",
            self.Statut.ALERTE_BASSE: "warn",
            self.Statut.NORMAL: "good",
            self.Statut.ALERTE_HAUTE: "warn",
            self.Statut.PLEIN: "bad",
        }.get(self.statut, "good")

    @property
    def est_en_alerte(self):
        return self.statut != self.Statut.NORMAL

    # ------------------------------------------------------------------
    # Règles de cohérence
    # ------------------------------------------------------------------
    def clean(self):
        erreurs = {}
        cap = self.capacite_max
        smin = self.seuil_alerte_min
        smax = self.seuil_alerte_max

        if smin is not None and smax is not None and smin >= smax:
            erreurs["seuil_alerte_min"] = "Le seuil minimum doit être inférieur au seuil maximum."
        if cap is not None and smax is not None and smax > cap:
            erreurs["seuil_alerte_max"] = "Le seuil maximum ne peut pas dépasser la capacité maximale."

        if self.pk:
            occupe = self.calculer_quantite()
            if cap is not None and cap < occupe:
                erreurs["capacite_max"] = (
                    f"La capacité ne peut pas être inférieure au volume déjà occupé "
                    f"({formater(occupe)} {UNITE})."
                )

        if erreurs:
            raise ValidationError(erreurs)

    # ------------------------------------------------------------------
    # Calculs automatiques
    # ------------------------------------------------------------------
    def calculer_indicateurs(self):
        if self.capacite_max and self.capacite_max > 0:
            taux = self.quantite_actuelle / self.capacite_max * 100
            self.taux_remplissage = min(taux, Decimal("100")).quantize(Decimal("0.01"))
        else:
            self.taux_remplissage = Decimal("0")

        q = self.quantite_actuelle
        if q <= 0:
            self.statut = self.Statut.VIDE
        elif q >= self.capacite_max:
            self.statut = self.Statut.PLEIN
        elif q <= self.seuil_alerte_min:
            self.statut = self.Statut.ALERTE_BASSE
        elif q >= self.seuil_alerte_max:
            self.statut = self.Statut.ALERTE_HAUTE
        else:
            self.statut = self.Statut.NORMAL

    def save(self, *args, **kwargs):
        # La quantité actuelle est toujours recalculée à partir des produits affectés
        if self.pk:
            self.quantite_actuelle = self.calculer_quantite()
        self.calculer_indicateurs()
        super().save(*args, **kwargs)

    def recalculer(self):
        """Appelé automatiquement (signals.py) quand un produit du stock change."""
        self.save()
