from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Stock(models.Model):
    TYPE_PRODUIT = [
        ("miel", "Miel"),
        ("cire", "Cire"),
        ("pollen", "Pollen"),
        ("propolis", "Propolis"),
        ("gelee_royale", "Gelée royale"),
    ]
    UNITES = [
        ("kg", "Kilogramme"),
        ("g", "Gramme"),
        ("pot", "Pot"),
    ]

    produit = models.CharField(max_length=30, choices=TYPE_PRODUIT)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    unite = models.CharField(max_length=10, choices=UNITES, default="kg")
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.DecimalField(max_digits=10, decimal_places=2)
    emplacement = models.CharField(max_length=100, blank=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(capacite_max__gt=0), name="stock_capacite_positive"),
            models.CheckConstraint(condition=Q(quantite__gte=0), name="stock_quantite_non_negative"),
            models.CheckConstraint(condition=Q(seuil_alerte__gte=0), name="stock_seuil_non_negative"),
            models.CheckConstraint(
                condition=Q(quantite__lte=F("capacite_max")),
                name="stock_quantite_within_capacity",
            ),
            models.CheckConstraint(
                condition=Q(seuil_alerte__lte=F("capacite_max")),
                name="stock_seuil_within_capacity",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.capacite_max is not None and self.capacite_max <= 0:
            errors["capacite_max"] = "La capacité maximale doit être supérieure à zéro."
        if self.quantite is not None and self.quantite < 0:
            errors["quantite"] = "La quantité ne peut pas être négative."
        if self.seuil_alerte is not None and self.seuil_alerte < 0:
            errors["seuil_alerte"] = "Le seuil d’alerte ne peut pas être négatif."
        if self.quantite is not None and self.capacite_max is not None and self.quantite > self.capacite_max:
            errors["quantite"] = "La quantité dépasse la capacité maximale."
        if self.seuil_alerte is not None and self.capacite_max is not None and self.seuil_alerte > self.capacite_max:
            errors["seuil_alerte"] = "Le seuil doit être inférieur ou égal à la capacité maximale."

        if errors:
            raise ValidationError(errors)

    def libelle_produit(self):
        """Centralise le nom affiché, y compris lors d’un futur passage à une ForeignKey."""
        produit = self.produit
        if isinstance(produit, str):
            return self.get_produit_display()
        return (
            getattr(produit, "nom", None)
            or getattr(produit, "nom_produit", None)
            or str(produit)
        )

    def icone(self):
        """Retourne une icône simple selon le type de produit apicole."""
        icones = {
            "miel": "🍯",
            "cire": "🕯️",
            "pollen": "🌼",
            "propolis": "🌿",
            "gelee_royale": "👑",
        }
        return icones.get(getattr(self.produit, "code", self.produit), "📦")

    def en_alerte(self):
        return self.quantite <= self.seuil_alerte

    def etat_disponibilite(self):
        if self.quantite <= 0:
            return "epuise"
        if self.en_alerte():
            return "bientot_epuise"
        return "disponible"

    def taux_remplissage(self):
        if self.capacite_max and self.capacite_max > 0:
            return round(self.quantite / self.capacite_max * 100, 1)
        return 0

    def __str__(self):
        return f"{self.libelle_produit()} — {self.quantite} {self.unite}"
