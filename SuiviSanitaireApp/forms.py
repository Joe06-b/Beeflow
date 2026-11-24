from django import forms

from rucheapp.models import Ruche

from .maladies import noms_maladies
from .models import EtatSante, NiveauRisque, SuiviSanitaire


class SuiviSanitaireForm(forms.ModelForm):
    """Formulaire d'ajout / modification d'un suivi sanitaire.
    Les règles de SuiviSanitaire.clean() sont appliquées automatiquement."""

    class Meta:
        model = SuiviSanitaire
        fields = [
            "ruche",
            "date_suivi",
            "etat_sante",
            "maladie_detectee",
            "symptomes",
            "observation",
            "type_traitement",
            "dose",
            "date_traitement",
            "date_prochain_controle",
            "niveau_risque",
        ]
        widgets = {
            "date_suivi": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_traitement": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_prochain_controle": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "symptomes": forms.Textarea(attrs={"rows": 3, "placeholder": "Ex : abeilles traînantes, ailes déformées..."}),
            "observation": forms.Textarea(attrs={"rows": 3, "placeholder": "Remarques de l'apiculteur"}),
            "maladie_detectee": forms.TextInput(attrs={"placeholder": "Ex : Varroase, Loque américaine..."}),
            "type_traitement": forms.TextInput(attrs={"placeholder": "Ex : Acide oxalique"}),
            "dose": forms.TextInput(attrs={"placeholder": "Ex : 5 ml / cadre"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "bf-select" if isinstance(field.widget, forms.Select) else "bf-input"
            field.widget.attrs["class"] = css
        # Liste déroulante alimentée par les vraies ruches (app rucheapp), triées par code
        self.fields["ruche"].queryset = Ruche.objects.order_by("code_ruche")
        self.fields["ruche"].empty_label = "Choisir une ruche"
        # Suggestions de l'atlas des maladies dans le champ libre (liste <datalist>)
        self.fields["maladie_detectee"].widget.attrs["list"] = "maladies-connues"
        self.fields["maladie_detectee"].widget.attrs["autocomplete"] = "off"
        self.maladies_connues = noms_maladies()


class RechercheSuiviForm(forms.Form):
    """Formulaire GET de recherche / filtre / tri."""

    TRI_CHOICES = [
        ("date_desc", "Tri : plus récents"),
        ("date_asc", "Tri : plus anciens"),
        ("ruche", "Tri : par ruche"),
        ("etat", "Tri : critiques"),
        ("risque", "Tri : risque élevé"),
        ("controle", "Tri : prochain contrôle"),
    ]

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Rechercher une maladie, un traitement, une ruche…", "aria-label": "Rechercher", "class": "bf-input"}),
    )
    ruche = forms.ModelChoiceField(
        required=False,
        queryset=Ruche.objects.order_by("code_ruche"),
        empty_label="Toutes les ruches",
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    etat_sante = forms.ChoiceField(
        required=False,
        choices=[("", "Tous les états")] + EtatSante.choices,
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    niveau_risque = forms.ChoiceField(
        required=False,
        choices=[("", "Tous les risques")] + NiveauRisque.choices,
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    tri = forms.ChoiceField(
        required=False, choices=TRI_CHOICES,
        widget=forms.Select(attrs={"class": "bf-select"}),
    )