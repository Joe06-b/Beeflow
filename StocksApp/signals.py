"""
Mise à jour automatique des stocks quand un produit change (module Produits).

Ajouter, modifier, déplacer ou supprimer un produit recalcule la quantité actuelle,
le taux de remplissage et le statut du ou des stocks concernés.
Les signaux ne sont branchés que si le modèle Produit possède la clé étrangère « stock » :
tant que ce n'est pas le cas, le module Stock fonctionne seul, sans erreur.
"""
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_save

PRODUIT_MODELE = ("ProduitApp", "Produit")
CHAMP_STOCK = "stock"


def _modele_produit():
    try:
        produit = apps.get_model(*PRODUIT_MODELE)
    except LookupError:
        return None
    try:
        produit._meta.get_field(CHAMP_STOCK)
    except FieldDoesNotExist:
        return None
    return produit


def _recalculer(stock_id):
    if not stock_id:
        return
    from .models import Stock
    stock = Stock.objects.filter(pk=stock_id).first()
    if stock is not None:
        stock.recalculer()


def _avant_enregistrement(sender, instance, **kwargs):
    # On retient l'ancien stock pour le mettre à jour si le produit est déplacé
    instance._ancien_stock_id = (
        sender.objects.filter(pk=instance.pk).values_list(f"{CHAMP_STOCK}_id", flat=True).first()
        if instance.pk else None
    )


def _apres_enregistrement(sender, instance, **kwargs):
    nouveau = getattr(instance, f"{CHAMP_STOCK}_id", None)
    ancien = getattr(instance, "_ancien_stock_id", None)
    _recalculer(nouveau)
    if ancien and ancien != nouveau:
        _recalculer(ancien)


def _apres_suppression(sender, instance, **kwargs):
    _recalculer(getattr(instance, f"{CHAMP_STOCK}_id", None))


def connecter_signaux_produits():
    produit = _modele_produit()
    if produit is None:
        return
    pre_save.connect(_avant_enregistrement, sender=produit, dispatch_uid="stocks_produit_pre_save")
    post_save.connect(_apres_enregistrement, sender=produit, dispatch_uid="stocks_produit_post_save")
    post_delete.connect(_apres_suppression, sender=produit, dispatch_uid="stocks_produit_post_delete")
