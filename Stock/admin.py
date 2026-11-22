from django.contrib import admin

from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "libelle_produit",
        "quantite",
        "unite",
        "capacite_max",
        "seuil_alerte",
        "emplacement",
        "etat_stock",
        "date_mise_a_jour",
    )
    list_filter = ("produit", "unite")
    search_fields = ("produit", "emplacement")
    readonly_fields = ("date_mise_a_jour",)
    ordering = ("produit", "emplacement")

    @admin.display(description="État")
    def etat_stock(self, stock):
        return {
            "disponible": "Disponible",
            "bientot_epuise": "Bientôt épuisé",
            "epuise": "Épuisé",
        }[stock.etat_disponibilite()]

    @admin.display(description="Produit", ordering="produit")
    def libelle_produit(self, stock):
        return stock.libelle_produit()
