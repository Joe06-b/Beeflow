from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = [
            "produit",
            "quantite",
            "unite",
            "capacite_max",
            "seuil_alerte",
            "emplacement",
        ]
        labels = {
            "produit": "Produit stocké",
            "quantite": "Quantité disponible",
            "unite": "Unité de mesure",
            "capacite_max": "Capacité maximale",
            "seuil_alerte": "Seuil d’alerte",
            "emplacement": "Emplacement",
        }
        help_texts = {
            "produit": "Choisissez le type de produit apicole suivi.",
            "quantite": "Saisissez la quantité actuellement disponible.",
            "unite": "Cette unité s’applique à la quantité, la capacité et au seuil.",
            "capacite_max": "La capacité doit être supérieure à zéro.",
            "seuil_alerte": "Une alerte apparaît quand la quantité atteint ce seuil.",
            "emplacement": "Facultatif : par exemple, réserve ou miellerie.",
        }
        widgets = {
            "produit": forms.Select(attrs={"class": "form-control"}),
            "quantite": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "unite": forms.Select(attrs={"class": "form-control"}),
            "capacite_max": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
            "seuil_alerte": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "emplacement": forms.TextInput(attrs={"class": "form-control", "maxlength": "100"}),
        }
