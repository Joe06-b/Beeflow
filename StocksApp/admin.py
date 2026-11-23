from django.contrib import admin

from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "nom_stock", "type_stock", "emplacement",
        "quantite_actuelle", "capacite_max", "taux_remplissage", "statut",
    )
    list_filter = ("type_stock", "statut")
    search_fields = ("nom_stock", "emplacement")
    readonly_fields = ("taux_remplissage", "statut", "date_creation", "date_modification")
    filter_horizontal = ("responsables",)