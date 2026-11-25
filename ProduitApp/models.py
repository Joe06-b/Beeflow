import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class EtatProduit(models.TextChoices):
    DISPONIBLE = "disponible", "Disponible"
    RUPTURE_STOCK = "rupture_stock", "Rupture de stock"
    ARCHIVE = "archive", "Archivé"


class Produit(models.Model):
    categorie_produit = models.CharField(max_length=30, choices=[
        ("miel", "Miel"),
        ("pollen", "Pollen"),
        ("propolis", "Propolis"),
        ("gelee_royale", "Gelée royale"),
        ("cire", "Cire"),
    ])
    origine_florale = models.CharField(max_length=100, blank=True)
    quantite = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"), "La quantité ne peut pas être négative.")],
    )
    unite = models.CharField(max_length=10, choices=[
        ("kg", "Kilogramme"),
        ("g", "Gramme"),
        ("l", "Litre"),
        ("ml", "Millilitre"),
    ], default="kg")
    volume_stockage = models.DecimalField(
        "Volume de stockage (m³)", max_digits=14, decimal_places=6,
        validators=[MinValueValidator(Decimal("0"), "Le volume de stockage ne peut pas être négatif.")],
    )
    prix = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"), "Le prix ne peut pas être négatif.")],
        help_text="Prix unitaire en dinars (TND).",
    )
    code_barre = models.CharField(max_length=13, unique=True, blank=True, null=True, editable=False)
    photo_produit = models.ImageField(upload_to="produits/", blank=True)
    description_sensorielle = models.TextField(blank=True)
    stock = models.ForeignKey(
        "StocksApp.Stock", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="produits",
        verbose_name="Stock d'affectation",
    )
    etat = models.CharField(max_length=20, choices=EtatProduit.choices, default=EtatProduit.DISPONIBLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_categorie_produit_display()} {self.origine_florale} ({self.quantite} {self.unite})"

    def clean(self):
        super().clean()
        if self.quantite is None:
            return
        if self.etat == EtatProduit.DISPONIBLE and self.quantite == 0:
            raise ValidationError({"etat": "Un produit disponible doit avoir une quantité supérieure à 0."})
        if self.etat == EtatProduit.RUPTURE_STOCK and self.quantite > 0:
            raise ValidationError({"etat": "Un produit en rupture de stock doit avoir une quantité égale à 0."})

    def save(self, *args, **kwargs):
        # Génération du code-barres si absent (EAN-13)
        if not self.code_barre:
            self.code_barre = self._generate_code_barre()
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_code_barre():
        """Génère un code EAN-13 unique (12 chiffres + clé de contrôle)."""
        while True:
            base = "".join(str(random.randint(0, 9)) for _ in range(12))
            total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(base))
            cle = (10 - total % 10) % 10
            code = f"{base}{cle}"
            if not Produit.objects.filter(code_barre=code).exists():
                return code
