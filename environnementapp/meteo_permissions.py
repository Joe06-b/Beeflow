"""Permissions spécifiques aux nouvelles API météo du Backoffice."""

from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode


def meteo_admin_page_requis(view_func):
    """Protège le Backoffice Environnement, sauf en développement local."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if settings.DEBUG:
            return view_func(request, *args, **kwargs)

        user = request.user
        if not user.is_authenticated:
            destination = reverse("admin:login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{destination}?{query}")
        if not user.is_staff:
            return HttpResponseForbidden("Accès réservé au personnel autorisé.")
        return view_func(request, *args, **kwargs)

    return wrapper


def meteo_admin_api_requis(view_func):
    """Protège l'API Backoffice sans rediriger les clients JSON vers du HTML."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if settings.DEBUG:
            return view_func(request, *args, **kwargs)

        user = request.user
        if not user.is_authenticated:
            return JsonResponse(
                {
                    "error": {
                        "code": "authentication_required",
                        "message": "Une authentification est requise.",
                    }
                },
                status=401,
            )
        if not user.is_staff:
            return JsonResponse(
                {
                    "error": {
                        "code": "permission_denied",
                        "message": "Accès réservé au personnel autorisé.",
                    }
                },
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return wrapper
