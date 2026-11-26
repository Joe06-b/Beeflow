from django.apps import AppConfig


class StocksappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "StocksApp"
    verbose_name = "Gestion du stock"

    def ready(self):
        # Mise à jour automatique des stocks quand un produit change (voir signals.py)
        from .signals import connecter_signaux_produits
        connecter_signaux_produits()
