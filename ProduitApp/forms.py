from decimal import Decimal

from django import forms
from django.db.models import Sum

from StocksApp.models import Stock
from .models import EtatProduit, Produit


class StockSelect(forms.Select):
    """<option> enrichies : data-restant (place restante, m³) et data-type (type du stock)."""
    infos = {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        pk = getattr(value, "value", value)
        option["attrs"].update(self.infos.get(pk, {}))
        return option


class ProduitForm(forms.ModelForm):
    """Formulaire d'ajout / modification (les règles de Produit.clean() s'appliquent)."""

    class Meta:
        model = Produit
        fields = [
            "categorie_produit",
            "origine_florale",
            "quantite",
            "unite",
            "volume_stockage",
            "prix",
            "etat",
            "stock",
            "photo_produit",
            "description_sensorielle",
        ]
        labels = {
            "categorie_produit": "Catégorie du produit",
            "origine_florale": "Origine florale (ex: Lavande, Romarin...)",
            "quantite": "Quantité",
            "unite": "Unité de mesure",
            "volume_stockage": "Volume de stockage (m³) pour toute la quantité",
            "prix": "Prix unitaire (TND)",
            "etat": "État du produit",
            "stock": "Stock d'affectation (ID)",
            "photo_produit": "Photo du produit",
            "description_sensorielle": "Description sensorielle (goût, odeur, texture...)",
        }
        widgets = {
            "description_sensorielle": forms.Textarea(attrs={"rows": 4}),
            "origine_florale": forms.TextInput(attrs={"placeholder": "Ex: Fleurs sauvages"}),
            "prix": forms.NumberInput(attrs={"placeholder": "Ex: 25.50", "step": "0.01"}),
            "volume_stockage": forms.NumberInput(attrs={"placeholder": "Ex: 0.035", "step": "any", "min": "0"}),
            "stock": StockSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Volume déjà occupé (m³) = Σ volume_stockage des AUTRES produits affectés
        occupe = Produit.objects.exclude(stock__isnull=True).order_by()
        if self.instance.pk:
            occupe = occupe.exclude(pk=self.instance.pk)
        occupes = dict(occupe.values_list("stock").annotate(total=Sum("volume_stockage")))
        stocks = list(Stock.objects.order_by("id"))
        self.restants = {s.pk: max(s.capacite_max - Decimal(str(occupes.get(s.pk) or 0)), Decimal("0")) for s in stocks}
        self.types_stock = {s.pk: s.type_stock.lower() for s in stocks}
        self.fields["stock"].widget.infos = {
            s.pk: {"data-restant": str(self.restants[s.pk]), "data-type": self.types_stock[s.pk]} for s in stocks
        }

        self.fields["stock"].queryset = Stock.objects.order_by("id")
        self.fields["stock"].required = True
        self.fields["stock"].empty_label = "— Choisir un stock —"
        self.fields["stock"].label_from_instance = (
            lambda s: f"#{s.pk} – {s.nom_stock} ({s.get_type_stock_display()}) · reste {float(self.restants.get(s.pk, Decimal('0'))):g} m³"
        )
        self.fields["stock"].error_messages["required"] = "Veuillez choisir le stock d'affectation."
        for name, field in self.fields.items():
            if name == "photo_produit":
                continue
            css = "bf-select" if isinstance(field.widget, forms.Select) else "bf-input"
            field.widget.attrs["class"] = css

    def clean(self):
        cleaned = super().clean()
        stock, categorie = cleaned.get("stock"), cleaned.get("categorie_produit")
        quantite, volume = cleaned.get("quantite"), cleaned.get("volume_stockage")
        if quantite is not None and volume is not None and quantite > 0 and volume <= 0:
            self.add_error("volume_stockage", "Le volume de stockage doit être supérieur à 0 quand la quantité est supérieure à 0.")
        if stock:
            if categorie and self.types_stock.get(stock.pk) != categorie:
                self.add_error("stock", f"Le type du stock ({stock.get_type_stock_display()}) ne correspond pas à la catégorie du produit.")
            elif volume is not None:
                restant = self.restants.get(stock.pk, Decimal("0"))
                if restant <= 0:
                    self.add_error("stock", f"Le stock « {stock.nom_stock} » est plein.")
                elif volume > restant:
                    self.add_error("stock", f"Capacité insuffisante : il reste {float(restant):g} m³ dans « {stock.nom_stock} », ce produit occupe {float(volume):g} m³.")
        return cleaned


class RechercheProduitForm(forms.Form):
    """Formulaire GET (affichage de la barre de recherche / filtres / tri).
    Le filtrage lui-même est fait dans services.filtrer_produits()."""

    TRI_CHOICES = [
        ("identifiant", "Tri : identifiant"),
        ("prix", "Tri : prix"),
        ("quantite", "Tri : quantité"),
    ]
    SENS_CHOICES = [
        ("asc", "Ordre croissant"),
        ("desc", "Ordre décroissant"),
    ]

    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "placeholder": "Identifiant ou code-barres", "aria-label": "Rechercher par identifiant ou code-barres",
        "class": "bf-input", "type": "search",
    }))
    categorie = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "bf-select", "aria-label": "Catégorie"}))
    origine = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "bf-select", "aria-label": "Origine florale"}))
    etat = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "bf-select", "aria-label": "État"}))
    tri = forms.ChoiceField(required=False, choices=TRI_CHOICES, widget=forms.Select(attrs={"class": "bf-select", "aria-label": "Trier par"}))
    sens = forms.ChoiceField(required=False, choices=SENS_CHOICES, widget=forms.Select(attrs={"class": "bf-select", "aria-label": "Ordre"}))

    def __init__(self, *args, origines=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].choices = [("", "Toutes les catégories")] + list(Produit._meta.get_field("categorie_produit").choices)
        self.fields["origine"].choices = [("", "Toutes les origines")] + [(o, o) for o in origines]
        self.fields["etat"].choices = [("", "Tous les états")] + list(EtatProduit.choices)
