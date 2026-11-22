from django import forms

from .models import EtatSante, NiveauRisque, RUCHES_TEST, SuiviSanitaire


class SuiviSanitaireForm(forms.ModelForm):
    """Formulaire d'ajout / modification d'un suivi sanitaire.
    Les règles de SuiviSanitaire.clean() sont appliquées automatiquement."""

    class Meta:
        model = SuiviSanitaire
        fields = [
            "id_ruche",
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
        self.fields["id_ruche"].choices = [("", "Choisir une ruche")] + RUCHES_TEST


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
    ruche = forms.TypedChoiceField(
        required=False, coerce=int, empty_value=None,
        choices=[("", "Toutes les ruches")] + RUCHES_TEST,
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