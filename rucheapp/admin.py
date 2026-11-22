from django.contrib import admin

from .models import HistoriqueRuche, Ruche


@admin.register(Ruche)
class RucheAdmin(admin.ModelAdmin):
    list_display = (
        "code_ruche",
        "type_ruche",
        "race_abeilles",
        "date_installation",
        "presence_reine",
        "nombre_abeilles",
        "etat_predit",
    )
    list_filter = ("presence_reine", "etat_predit", "type_ruche")
    search_fields = ("code_ruche", "type_ruche", "race_abeilles")
    ordering = ("code_ruche",)


@admin.register(HistoriqueRuche)
class HistoriqueRucheAdmin(admin.ModelAdmin):
    list_display = ("code_ruche", "action", "auteur", "date_modification")
    list_filter = ("action", "date_modification")
    search_fields = ("code_ruche", "auteur")
    readonly_fields = (
        "ruche",
        "code_ruche",
        "action",
        "changements",
        "donnees",
        "auteur",
        "date_modification",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
