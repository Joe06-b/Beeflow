from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    """Formulaire d'ajout / modification d'un stock.
    Les règles de Stock.clean() sont appliquées automatiquement ;
    taux_remplissage et statut sont calculés dans Stock.save()."""

    class Meta:
        model = Stock
        fields = [
            "nom_stock",
            "type_stock",
            "emplacement",
            "description",
            "capacite_max",
            "quantite_actuelle",
            "seuil_alerte_min",
            "seuil_alerte_max",
            "responsables",
        ]
        widgets = {
            "nom_stock": forms.TextInput(attrs={"placeholder": "Ex : Miel de printemps 2026"}),
            "emplacement": forms.TextInput(attrs={"placeholder": "Ex : Entrepôt A – étagère 2"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Remarques sur ce stock"}),
            "capacite_max": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Ex : 500"}),
            "quantite_actuelle": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Ex : 120"}),
            "seuil_alerte_min": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Ex : 50"}),
            "seuil_alerte_max": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Ex : 450"}),
            "responsables": forms.SelectMultiple(attrs={"size": 4}),
        }
        help_texts = {
            "seuil_alerte_min": "Alerte basse si la quantité descend à ce niveau.",
            "seuil_alerte_max": "Alerte haute si la quantité atteint ce niveau.",
            "responsables": "Ctrl + clic pour en sélectionner plusieurs.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "bf-select" if isinstance(field.widget, forms.Select) else "bf-input"
            field.widget.attrs["class"] = css
            
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
        ("quantite", "Tri : quantité"),
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