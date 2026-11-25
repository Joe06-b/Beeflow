
from django import forms

from .models import (
    Environnement,
    TypeVegetation,
    NiveauFloraison,
    NiveauRisque,
)


class EnvironnementForm(forms.ModelForm):
    """Formulaire d'ajout et de modification d'une zone environnementale."""

    class Meta:
        model = Environnement
        fields = [
            "idZone",
            "nomZone",
            "latitude",
            "longitude",
            "typeVegetation",
            "surface",
            "temperature",
            "humidite",
            "precipitation",
            "vitesseVent",
            "niveauFloraison",
            "dateMesure",
        ]

        widgets = {
            "idZone": forms.NumberInput(attrs={
                "class": "bf-input",
                "readonly": "readonly",
            }),
            "nomZone": forms.TextInput(attrs={
                "class": "bf-input",
                "placeholder": "Nom de la zone",
            }),
            "latitude": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "longitude": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "typeVegetation": forms.Select(attrs={
                "class": "bf-select",
            }),
            "surface": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "temperature": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "humidite": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "precipitation": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "vitesseVent": forms.NumberInput(attrs={
                "class": "bf-input",
                "step": "any",
            }),
            "niveauFloraison": forms.Select(attrs={
                "class": "bf-select",
            }),
            "dateMesure": forms.DateTimeInput(attrs={
                "class": "bf-input",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
        }


class RechercheEnvironnementForm(forms.Form):
    """Recherche, filtres simples, filtres avancés et tri des environnements."""

    FILTRES_AVANCES = (
        "surface_min",
        "surface_max",
        "temperature_min",
        "temperature_max",
        "humidite_min",
        "humidite_max",
        "precipitation_min",
        "precipitation_max",
        "vitesseVent_min",
        "vitesseVent_max",
        "date_debut",
        "date_fin",
    )

    # Recherche textuelle
    q = forms.CharField(
        required=False,
        label="Rechercher une zone",
        widget=forms.TextInput(attrs={
            "class": "bf-input",
            "placeholder": "Nom de la zone...",
        }),
    )

    # Filtres principaux
    type_vegetation = forms.ChoiceField(
        required=False,
        label="Type de végétation",
        choices=[("", "Toutes les végétations")] + list(TypeVegetation.choices),
        widget=forms.Select(attrs={
            "class": "bf-select",
        }),
    )

    niveau_floraison = forms.ChoiceField(
        required=False,
        label="Niveau de floraison",
        choices=[("", "Toutes les floraisons")] + list(NiveauFloraison.choices),
        widget=forms.Select(attrs={
            "class": "bf-select",
        }),
    )

    niveau_risque = forms.ChoiceField(
        required=False,
        label="Niveau de risque",
        choices=[("", "Tous les niveaux de risque")] + list(NiveauRisque.choices),
        widget=forms.Select(attrs={
            "class": "bf-select",
        }),
    )

    # Filtres avancés : surface
    surface_min = forms.FloatField(
        required=False,
        label="Surface minimale (ha)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Minimum",
            "step": "any",
            "min": "0",
        }),
    )

    surface_max = forms.FloatField(
        required=False,
        label="Surface maximale (ha)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Maximum",
            "step": "any",
            "min": "0",
        }),
    )

    # Filtres avancés : température
    temperature_min = forms.FloatField(
        required=False,
        label="Température minimale (°C)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Minimum",
            "step": "any",
        }),
    )

    temperature_max = forms.FloatField(
        required=False,
        label="Température maximale (°C)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Maximum",
            "step": "any",
        }),
    )

    # Filtres avancés : humidité
    humidite_min = forms.FloatField(
        required=False,
        label="Humidité minimale (%)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Minimum",
            "step": "any",
            "min": "0",
            "max": "100",
        }),
    )

    humidite_max = forms.FloatField(
        required=False,
        label="Humidité maximale (%)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Maximum",
            "step": "any",
            "min": "0",
            "max": "100",
        }),
    )

    # Filtres avancés : précipitations
    precipitation_min = forms.FloatField(
        required=False,
        label="Précipitations minimales (mm)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Minimum",
            "step": "any",
            "min": "0",
        }),
    )

    precipitation_max = forms.FloatField(
        required=False,
        label="Précipitations maximales (mm)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Maximum",
            "step": "any",
            "min": "0",
        }),
    )

    # Filtres avancés : vitesse du vent
    vitesseVent_min = forms.FloatField(
        required=False,
        label="Vitesse minimale du vent (km/h)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Minimum",
            "step": "any",
            "min": "0",
        }),
    )

    vitesseVent_max = forms.FloatField(
        required=False,
        label="Vitesse maximale du vent (km/h)",
        widget=forms.NumberInput(attrs={
            "class": "bf-input",
            "placeholder": "Maximum",
            "step": "any",
            "min": "0",
        }),
    )

    # Filtres avancés : période de mesure
    date_debut = forms.DateField(
        required=False,
        label="Date de début",
        widget=forms.DateInput(attrs={
            "class": "bf-input",
            "type": "date",
        }),
    )

    date_fin = forms.DateField(
        required=False,
        label="Date de fin",
        widget=forms.DateInput(attrs={
            "class": "bf-input",
            "type": "date",
        }),
    )

    # Tri
    TRI_CHOICES = [
        ("date_desc", "Date : plus récente"),
        ("date_asc", "Date : plus ancienne"),
        ("nom_asc", "Nom : A → Z"),
        ("surface_asc", "Surface : croissante"),
        ("surface_desc", "Surface : décroissante"),
        ("risque_asc", "Niveau de risque : faible à critique"),
    ]

    tri = forms.ChoiceField(
        required=False,
        label="Trier par",
        choices=TRI_CHOICES,
        initial="date_desc",
        widget=forms.Select(attrs={
            "class": "bf-select",
        }),
    )

    @property
    def filtres_avances_actifs(self):
        return self.is_bound and any(
            self[name].value() not in (None, "")
            for name in self.FILTRES_AVANCES
        )

    def clean(self):
        cleaned_data = super().clean()

        # Vérification des intervalles numériques
        intervalles = [
            ("surface_min", "surface_max", "surface"),
            ("temperature_min", "temperature_max", "température"),
            ("humidite_min", "humidite_max", "humidité"),
            ("precipitation_min", "precipitation_max", "précipitations"),
            ("vitesseVent_min", "vitesseVent_max", "vitesse du vent"),
        ]

        for champ_min, champ_max, nom in intervalles:
            minimum = cleaned_data.get(champ_min)
            maximum = cleaned_data.get(champ_max)

            if minimum is not None and maximum is not None:
                if minimum > maximum:
                    self.add_error(
                        champ_max,
                        f"La valeur maximale de {nom} doit être supérieure ou égale à la valeur minimale.",
                    )

        # Vérification de la période
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        if date_debut and date_fin and date_debut > date_fin:
            self.add_error(
                "date_fin",
                "La date de fin doit être postérieure ou égale à la date de début.",
            )

        # Vérification des limites métier
        if cleaned_data.get("surface_min") is not None and cleaned_data["surface_min"] < 0:
            self.add_error("surface_min", "La surface minimale ne peut pas être négative.")

        if cleaned_data.get("humidite_min") is not None and not 0 <= cleaned_data["humidite_min"] <= 100:
            self.add_error("humidite_min", "L'humidité doit être comprise entre 0 et 100 %.")

        if cleaned_data.get("humidite_max") is not None and not 0 <= cleaned_data["humidite_max"] <= 100:
            self.add_error("humidite_max", "L'humidité doit être comprise entre 0 et 100 %.")

        for champ in (
            "precipitation_min",
            "precipitation_max",
            "vitesseVent_min",
            "vitesseVent_max",
        ):
            valeur = cleaned_data.get(champ)
            if valeur is not None and valeur < 0:
                self.add_error(champ, "Cette valeur ne peut pas être négative.")

        return cleaned_data


class StatistiquesEnvironnementForm(forms.Form):
    """Filtres combinables de la page statistiques du Backoffice."""

    type_vegetation = forms.ChoiceField(
        required=False,
        label="Type de végétation",
        choices=[("", "Tous les types")] + list(TypeVegetation.choices),
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    niveau_floraison = forms.ChoiceField(
        required=False,
        label="Niveau de floraison",
        choices=[("", "Tous les niveaux")] + list(NiveauFloraison.choices),
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    niveau_risque = forms.ChoiceField(
        required=False,
        label="Niveau de risque",
        choices=[("", "Tous les niveaux")] + list(NiveauRisque.choices),
        widget=forms.Select(attrs={"class": "bf-select"}),
    )
    date_debut = forms.DateField(
        required=False,
        label="Date de début",
        widget=forms.DateInput(attrs={"class": "bf-input", "type": "date"}),
    )
    date_fin = forms.DateField(
        required=False,
        label="Date de fin",
        widget=forms.DateInput(attrs={"class": "bf-input", "type": "date"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        if date_debut and date_fin and date_debut > date_fin:
            self.add_error(
                "date_fin",
                "La date de fin doit être postérieure ou égale à la date de début.",
            )
        return cleaned_data
