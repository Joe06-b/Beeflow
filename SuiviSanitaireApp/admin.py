from django.contrib import admin

from .models import SuiviSanitaire


@admin.register(SuiviSanitaire)
class SuiviSanitaireAdmin(admin.ModelAdmin):
    list_display = ("id_suivi", "ruche", "date_suivi", "etat_sante", "niveau_risque", "maladie_detectee", "date_prochain_controle")
    list_filter = ("etat_sante", "niveau_risque", "ruche")
    search_fields = ("maladie_detectee", "symptomes", "observation", "type_traitement", "ruche__code_ruche")
    list_select_related = ("ruche",)
    date_hierarchy = "date_suivi"
