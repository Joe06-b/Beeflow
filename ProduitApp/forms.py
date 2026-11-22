from django import forms

from .models import EtatProduit, Produit


class ProduitForm(forms.ModelForm):
    """Formulaire d'ajout / modification (les règles de Produit.clean() s'appliquent)."""

    class Meta:
        model = Produit
        fields = [
            "categorie_produit",
            "origine_florale",
            "quantite",
            "unite",
            "prix",
            "etat",
            "photo_produit",
            "description_sensorielle",
        ]
        labels = {
            "categorie_produit": "Catégorie du produit",
            "origine_florale": "Origine florale (ex: Lavande, Romarin...)",
            "quantite": "Quantité en stock",
            "unite": "Unité de mesure",
            "prix": "Prix unitaire (TND)",
            "etat": "État du produit",
            "photo_produit": "Photo du produit",
            "description_sensorielle": "Description sensorielle (goût, odeur, texture...)",
        }
        widgets = {
            "description_sensorielle": forms.Textarea(attrs={"rows": 4}),
            "origine_florale": forms.TextInput(attrs={"placeholder": "Ex: Fleurs sauvages"}),
            "prix": forms.NumberInput(attrs={"placeholder": "Ex: 25.50", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "photo_produit":
                continue
            css = "bf-select" if isinstance(field.widget, forms.Select) else "bf-input"
            field.widget.attrs["class"] = css


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
