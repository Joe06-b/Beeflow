from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    """Formulaire d'ajout / modification d'un stock.
    Les règles de Stock.clean() sont appliquées automatiquement.
    La quantité actuelle (m³), le taux de remplissage et le statut sont calculés
    à partir des volumes des produits affectés au stock : ils ne sont pas saisis ici."""

    class Meta:
        model = Stock
        fields = [
            "nom_stock",
            "type_stock",
            "emplacement",
            "description",
            "capacite_max",
            "seuil_alerte_min",
            "seuil_alerte_max",
            "responsables",
        ]
        widgets = {
            "nom_stock": forms.TextInput(attrs={"placeholder": "Ex : Cuve à miel A"}),
            "emplacement": forms.TextInput(attrs={"placeholder": "Ex : Miellerie – chambre froide 1"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Remarques sur ce stock"}),
            "capacite_max": forms.NumberInput(attrs={"step": "0.001", "min": "0", "placeholder": "Ex : 2.5"}),
            "seuil_alerte_min": forms.NumberInput(attrs={"step": "0.001", "min": "0", "placeholder": "Ex : 0.25"}),
            "seuil_alerte_max": forms.NumberInput(attrs={"step": "0.001", "min": "0", "placeholder": "Ex : 2.25"}),
            "responsables": forms.SelectMultiple(attrs={"size": 4}),
        }
        help_texts = {
            "capacite_max": "Volume total de rangement du stock, en m³ (1 m³ = 1 000 litres).",
            "seuil_alerte_min": "Alerte basse si le volume occupé descend à ce niveau (m³).",
            "seuil_alerte_max": "Alerte haute si le volume occupé atteint ce niveau (m³).",
            "responsables": "Ctrl + clic pour en sélectionner plusieurs.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "bf-select" if isinstance(field.widget, forms.Select) else "bf-input"
            field.widget.attrs["class"] = css
        # Association « Controler » : seuls les profils métier peuvent contrôler un stock
        self.fields["responsables"].queryset = (
            self.fields["responsables"].queryset.filter(role__in=["responsable", "apiculteur"]).order_by("username")
        )


class RechercheStockForm(forms.Form):
    """Formulaire GET de recherche / filtre / tri."""

    TRI_CHOICES = [
        ("nom", "Tri : nom (A → Z)"),
        ("recent", "Tri : plus récents"),
        ("alerte", "Tri : alertes d'abord"),
        ("remplissage_desc", "Tri : plus remplis"),
        ("remplissage_asc", "Tri : moins remplis"),
    ]

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Rechercher un stock, un emplacement…", "aria-label": "Rechercher", "class": "bf-input"}),
    )
    type_stock = forms.ChoiceField(
        required=False,
        choices=[("", "Tous les types")] + Stock.TypeStock.choices,
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    statut = forms.ChoiceField(
        required=False,
        choices=[("", "Tous les statuts")] + Stock.Statut.choices,
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    tri = forms.ChoiceField(
        required=False, choices=TRI_CHOICES,
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
