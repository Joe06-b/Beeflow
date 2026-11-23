from django.contrib import admin

from .models import Produit


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ("code_barre", "categorie_produit", "origine_florale", "quantite", "unite", "prix", "etat")
    list_filter = ("categorie_produit", "etat", "unite")
    search_fields = ("code_barre", "origine_florale", "description_sensorielle")
    readonly_fields = ("code_barre", "created_at", "updated_at")
    fieldsets = (
        ("Informations générales", {
            "fields": ("categorie_produit", "origine_florale", "description_sensorielle", "photo_produit")
        }),
        ("Stock et Prix", {
            "fields": ("quantite", "unite", "prix", "etat")
        }),
        ("Identifiants et dates", {
            "fields": ("code_barre", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
