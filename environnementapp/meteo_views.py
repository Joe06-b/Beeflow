"""API météo Frontoffice et Backoffice."""

import hashlib

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .meteo_permissions import meteo_admin_api_requis
from .meteo_service import (
    ApiMeteoIndisponible,
    CoordonneesInvalides,
    MeteoErreur,
    obtenir_previsions,
)
from .models import Environnement


ZONE_REFRESH_COOLDOWN = 15
ACTOR_REFRESH_COOLDOWN = 30


def _json_response(request, payload, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = (
        "private, no-store" if request.user.is_authenticated else "no-store"
    )
    return response


def _erreur(request, code, message, status, zone=None):
    payload = {
        "status": code,
        "error": {"code": code, "message": message},
    }
    if zone is not None:
        payload["zone"] = {"id": zone.idZone, "name": zone.nomZone}
    return _json_response(request, payload, status)


def _zone(pk):
    try:
        return Environnement.objects.get(pk=pk)
    except Environnement.DoesNotExist:
        return None


def _zone_payload(zone):
    return {
        "id": zone.idZone,
        "name": zone.nomZone,
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "environment": {
            "vegetation_type": zone.typeVegetation,
            "surface_hectares": zone.surface,
            "bloom_level": zone.niveauFloraison,
            "recorded_measurement": {
                "temperature_c": zone.temperature,
                "humidity_percent": zone.humidite,
                "precipitation_mm": zone.precipitation,
                "wind_speed_kmh": zone.vitesseVent,
                "measured_at": zone.dateMesure.isoformat(),
            },
        },
    }


def _weather_payload(zone, request, force=False):
    try:
        previsions = obtenir_previsions(
            zone.latitude,
            zone.longitude,
            force=force,
        )
    except CoordonneesInvalides:
        return _erreur(
            request,
            "sans_coordonnees",
            "Les coordonnées GPS de cette zone ne sont pas exploitables.",
            422,
            zone,
        )
    except ApiMeteoIndisponible:
        return _erreur(
            request,
            "api_indisponible",
            "Les données météo sont temporairement indisponibles.",
            502,
            zone,
        )
    except MeteoErreur:
        return _erreur(
            request,
            "reponse_invalide",
            "La réponse météo reçue ne peut pas être utilisée.",
            502,
            zone,
        )

    return _json_response(
        request,
        {
            "status": "available",
            "zone": _zone_payload(zone),
            **previsions,
        },
    )


def _actor_token(request):
    user = request.user
    if user.is_authenticated:
        actor = f"staff:{user.pk}"
    else:
        actor = f"remote:{request.META.get('REMOTE_ADDR', 'unknown')}"
    return hashlib.sha256(actor.encode("utf-8")).hexdigest()[:24]


def _actualisation_limitee(request, zone):
    """Limite les actualisations répétées par zone et par acteur."""
    zone_key = f"meteo:refresh:zone:{zone.pk}"
    actor_key = f"meteo:refresh:actor:{_actor_token(request)}"
    zone_allowed = cache.add(zone_key, True, ZONE_REFRESH_COOLDOWN)
    actor_allowed = cache.add(actor_key, True, ACTOR_REFRESH_COOLDOWN)
    return zone_allowed and actor_allowed


def _refresh(zone, request):
    if not _actualisation_limitee(request, zone):
        response = _erreur(
            request,
            "refresh_rate_limited",
            "Une actualisation récente est déjà en cours ou vient d'être effectuée.",
            429,
            zone,
        )
        response["Retry-After"] = str(ACTOR_REFRESH_COOLDOWN)
        return response
    return _weather_payload(zone, request, force=True)


@require_GET
def api_liste_zones(request):
    """Liste les zones sans déclencher d'appels météo."""
    zones = Environnement.objects.order_by("nomZone", "idZone")
    return _json_response(
        request,
        {
            "zones": [_zone_payload(zone) for zone in zones]
        },
    )


@require_GET
def api_meteo_zone(request, pk):
    zone = _zone(pk)
    if zone is None:
        return _erreur(request, "zone_introuvable", "Zone introuvable.", 404)
    return _weather_payload(zone, request)


@require_POST
def api_actualiser_meteo(request, pk):
    zone = _zone(pk)
    if zone is None:
        return _erreur(request, "zone_introuvable", "Zone introuvable.", 404)
    return _refresh(zone, request)


@meteo_admin_api_requis
@require_GET
def bo_api_liste_zones(request):
    """Liste administrative incluant les coordonnées GPS."""
    zones = Environnement.objects.order_by("nomZone", "idZone")
    return _json_response(
        request,
        {"zones": [_zone_payload(zone) for zone in zones]},
    )


@meteo_admin_api_requis
@require_GET
def bo_api_meteo_zone(request, pk):
    zone = _zone(pk)
    if zone is None:
        return _erreur(request, "zone_introuvable", "Zone introuvable.", 404)
    return _weather_payload(zone, request)


@meteo_admin_api_requis
@require_POST
def bo_api_actualiser_meteo(request, pk):
    zone = _zone(pk)
    if zone is None:
        return _erreur(request, "zone_introuvable", "Zone introuvable.", 404)
    return _refresh(zone, request)
