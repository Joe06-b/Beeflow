from django import forms

from .models import RaceAbeilles, Ruche, TypeRuche


class RucheForm(forms.ModelForm):
    type_ruche = forms.ChoiceField(
        choices=TypeRuche.choices,
        label="Type de ruche",
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    race_abeilles = forms.ChoiceField(
        choices=RaceAbeilles.choices,
        label="Race des abeilles",
        widget=forms.Select(attrs={"class": "bf-select"}),
    )

    class Meta:
        model = Ruche
        fields = [
            "code_ruche",
            "type_ruche",
            "race_abeilles",
            "date_installation",
            "presence_reine",
            "nombre_abeilles",
            "etat_predit",
            "user_id",
            "idZone",
        ]
        widgets = {
            "code_ruche": forms.TextInput(
                attrs={"class": "bf-input", "placeholder": "Ex. R-001", "autocomplete": "off"}
            ),
            "date_installation": forms.DateInput(
                attrs={"class": "bf-input", "type": "date"},
                format="%Y-%m-%d",
            ),
            "presence_reine": forms.CheckboxInput(attrs={"class": "rch-checkbox"}),
            "nombre_abeilles": forms.NumberInput(
                attrs={"class": "bf-input", "min": 1, "max": 2_000_000, "step": 1}
            ),
            "etat_predit": forms.Select(attrs={"class": "bf-select"}),
            "user_id": forms.NumberInput(
                attrs={"class": "bf-input", "min": 1, "placeholder": "Optionnel"}
            ),
            "idZone": forms.NumberInput(
                attrs={"class": "bf-input", "min": 1, "placeholder": "Optionnel"}
            ),
        }
        help_texts = {
            "code_ruche": "Code unique : lettres, chiffres et tirets uniquement.",
            "type_ruche": "Sélectionnez le modèle de la ruche.",
            "race_abeilles": "Sélectionnez la race principale de la colonie.",
            "date_installation": "La date ne peut pas être postérieure à aujourd'hui.",
            "presence_reine": "Décochez cette case si aucune reine n'est présente.",
            "nombre_abeilles": "Valeur comprise entre 1 et 2 000 000.",
            "etat_predit": "État courant ou résultat du modèle de prédiction.",
            "user_id": "Identifiant du propriétaire dans le module Utilisateur.",
            "idZone": "Identifiant optionnel de la zone dans le module Environnement.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["code_ruche"].disabled = True
            self.fields["code_ruche"].help_text = (
                "Le code identifie définitivement la ruche et ne peut pas être modifié."
            )

        # Préserver les anciennes valeurs libres lors de la modification d'une
        # ruche créée avant l'ajout des listes déroulantes.
        for nom_champ in ("type_ruche", "race_abeilles"):
            valeur = getattr(self.instance, nom_champ, "") if self.instance else ""
            valeurs_connues = {choix[0] for choix in self.fields[nom_champ].choices}
            if valeur and valeur not in valeurs_connues:
                self.fields[nom_champ].choices = [
                    (valeur, f"{valeur} (valeur existante)"),
                    *self.fields[nom_champ].choices,
                ]

    def clean_code_ruche(self):
        return self.cleaned_data["code_ruche"].strip().upper()

    def clean_type_ruche(self):
        return self.cleaned_data["type_ruche"].strip()

    def clean_race_abeilles(self):
        return self.cleaned_data["race_abeilles"].strip()
