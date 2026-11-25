from django.contrib import admin
from .models import Environnement


@admin.register(Environnement)
class EnvironnementAdmin(admin.ModelAdmin):
    list_display = (
        "idZone",
        "nomZone",
        "typeVegetation",
        "surface",
        "temperature",
        "humidite",
        "vitesseVent",
        "niveauFloraison",
        "dateMesure",
        "niveauRisque",
    )
    list_filter = ("typeVegetation", "niveauFloraison", "niveauRisque")
    search_fields = ("nomZone",)
    ordering = ("-dateMesure", "-idZone")
