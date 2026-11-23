"""
Contrôle d'accès du module Gestion du stock, aligné sur UtilisateursApp/mixins.py :
  - back office  : rôle "admin" uniquement (sinon -> espace)
  - front office : rôles métier + admin (sinon -> dashboard)
  - visiteur non connecté : renvoyé vers la page de connexion
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

# L'admin peut consulter le front office du stock (boutons de passage front <-> back)
ROLES_FRONT = ("apiculteur", "responsable", "admin")


def _role(user):
    return getattr(user, "role", None)


def admin_requis(view_func):
    """Back office : réservé au rôle admin."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if _role(request.user) != "admin":
            return redirect("espace")
        return view_func(request, *args, **kwargs)

    return wrapper


def metier_requis(view_func):
    """Front office : apiculteur, responsable production et stock, ou admin."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if _role(request.user) not in ROLES_FRONT:
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper