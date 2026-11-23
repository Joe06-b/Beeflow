from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Stock(models.Model):

    class TypeStock(models.TextChoices):
        MIEL = "MIEL", "Miel"
        CIRE = "CIRE", "Cire"
        POLLEN = "POLLEN", "Pollen"
        PROPOLIS = "PROPOLIS", "Propolis"
        GELEE_ROYALE = "GELEE_ROYALE", "Gelée royale"
        AUTRE = "AUTRE", "Autre"

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

    capacite_max = models.DecimalField(
        "Capacité maximale", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    quantite_actuelle = models.DecimalField(
        "Quantité actuelle", max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )
    seuil_alerte_min = models.DecimalField(
        "Seuil d'alerte minimum", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    seuil_alerte_max = models.DecimalField(
        "Seuil d'alerte maximum", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # Calculés automatiquement (non saisis par l'utilisateur)
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

    # --- Pour l'affichage (couleur du badge et de la jauge) ---
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
    
    # --- Règles de cohérence ---
    def clean(self):
        erreurs = {}
        cap = self.capacite_max
        qte = self.quantite_actuelle
        smin = self.seuil_alerte_min
        smax = self.seuil_alerte_max

        if cap is not None and qte is not None and qte > cap:
            erreurs["quantite_actuelle"] = "La quantité ne peut pas dépasser la capacité maximale."
        if smin is not None and smax is not None and smin >= smax:
            erreurs["seuil_alerte_min"] = "Le seuil minimum doit être inférieur au seuil maximum."
        if cap is not None and smax is not None and smax > cap:
            erreurs["seuil_alerte_max"] = "Le seuil maximum ne peut pas dépasser la capacité maximale."

        if erreurs:
            raise ValidationError(erreurs)

    # --- Calculs automatiques ---
    def calculer_indicateurs(self):
        if self.capacite_max and self.capacite_max > 0:
            taux = self.quantite_actuelle / self.capacite_max * 100
            self.taux_remplissage = taux.quantize(Decimal("0.01"))
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
        self.calculer_indicateurs()
        super().save(*args, **kwargs)