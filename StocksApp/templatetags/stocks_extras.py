"""Filtres de template du module Stock.  Usage : {% load stocks_extras %} puis {{ valeur|qte }}"""
from django import template

from ..models import formater

register = template.Library()


@register.filter
def qte(valeur):
    """Affiche une quantité sans zéros inutiles : 50.800 -> 50,8 ; 300.00 -> 300 ; 0.005 -> 0,005"""
    if valeur in (None, ""):
        return "—"
    try:
        return formater(valeur)
    except Exception:
        return valeur
