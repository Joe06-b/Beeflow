import mimetypes

from django.apps import AppConfig


class SuivisanitaireappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'SuiviSanitaireApp'

    def ready(self):
        # Sous Windows, le registre associe souvent les fichiers .js au type « text/plain ».
        # Django sert alors les scripts avec ce mauvais type, et le navigateur REFUSE d'exécuter
        # les modules JavaScript (la page 3D reste bloquée sur « Préparation de l'abeille… »).
        # On force les bons types une fois pour toutes, sans toucher à settings.py.
        mimetypes.add_type("text/javascript", ".js", True)
        mimetypes.add_type("text/javascript", ".mjs", True)
        mimetypes.add_type("text/css", ".css", True)
        mimetypes.add_type("image/svg+xml", ".svg", True)
