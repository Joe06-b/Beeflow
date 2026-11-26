"""Accès et normalisation des prévisions Open-Meteo."""

import json
import math
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils import timezone


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TIMEOUT = 20 * 60
REQUEST_TIMEOUT = 8
FORECAST_DAYS = 7

CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "surface_pressure",
    "visibility",
    "uv_index",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation",
    "rain",
    "cloud_cover",
    "weather_code",
    "is_day",
)
HOURLY_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "visibility",
    "uv_index",
    "precipitation_probability",
    "precipitation",
    "rain",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)
DAILY_FIELDS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "weather_code",
    "uv_index_max",
    "precipitation_probability_max",
    "precipitation_sum",
    "wind_speed_10m_max",
    "sunrise",
    "sunset",
)

CURRENT_NAMES = {
    "temperature_2m": "temperature_c",
    "apparent_temperature": "apparent_temperature_c",
    "relative_humidity_2m": "relative_humidity_percent",
    "surface_pressure": "surface_pressure_hpa",
    "visibility": "visibility_m",
    "uv_index": "uv_index",
    "wind_speed_10m": "wind_speed_kmh",
    "wind_direction_10m": "wind_direction_degrees",
    "wind_gusts_10m": "wind_gusts_kmh",
    "precipitation": "precipitation_mm",
    "rain": "rain_mm",
    "cloud_cover": "cloud_cover_percent",
    "weather_code": "weather",
    "is_day": "is_day",
}
HOURLY_NAMES = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_percent",
    "surface_pressure": "surface_pressure_hpa",
    "visibility": "visibility_m",
    "uv_index": "uv_index",
    "precipitation_probability": "precipitation_probability_percent",
    "precipitation": "precipitation_mm",
    "rain": "rain_mm",
    "weather_code": "weather",
    "cloud_cover": "cloud_cover_percent",
    "wind_speed_10m": "wind_speed_kmh",
    "wind_direction_10m": "wind_direction_degrees",
    "wind_gusts_10m": "wind_gusts_kmh",
}
DAILY_NAMES = {
    "temperature_2m_max": "temperature_max_c",
    "temperature_2m_min": "temperature_min_c",
    "weather_code": "weather",
    "uv_index_max": "uv_index_max",
    "precipitation_probability_max": "precipitation_probability_percent",
    "precipitation_sum": "precipitation_sum_mm",
    "wind_speed_10m_max": "wind_speed_max_kmh",
    "sunrise": "sunrise",
    "sunset": "sunset",
}

WMO_WEATHER = {
    0: ("Dégagé", "clear"),
    1: ("Principalement dégagé", "clear"),
    2: ("Partiellement nuageux", "cloudy"),
    3: ("Couvert", "cloudy"),
    45: ("Brouillard", "fog"),
    48: ("Brouillard givrant", "fog"),
    51: ("Bruine légère", "drizzle"),
    53: ("Bruine modérée", "drizzle"),
    55: ("Bruine dense", "drizzle"),
    56: ("Bruine verglaçante légère", "drizzle"),
    57: ("Bruine verglaçante dense", "drizzle"),
    61: ("Pluie faible", "rain"),
    63: ("Pluie modérée", "rain"),
    65: ("Pluie forte", "rain"),
    66: ("Pluie verglaçante légère", "rain"),
    67: ("Pluie verglaçante forte", "rain"),
    71: ("Chute de neige faible", "snow"),
    73: ("Chute de neige modérée", "snow"),
    75: ("Chute de neige forte", "snow"),
    77: ("Grains de neige", "snow"),
    80: ("Averses faibles", "rain"),
    81: ("Averses modérées", "rain"),
    82: ("Averses violentes", "rain"),
    85: ("Averses de neige faibles", "snow"),
    86: ("Averses de neige fortes", "snow"),
    95: ("Orage", "storm"),
    96: ("Orage avec grêle faible", "storm"),
    99: ("Orage avec grêle forte", "storm"),
}


class MeteoErreur(Exception):
    """Erreur attendue lors de la récupération ou lecture des prévisions."""


class CoordonneesInvalides(MeteoErreur):
    """Les coordonnées de la zone ne peuvent pas être utilisées."""


class ApiMeteoIndisponible(MeteoErreur):
    """Open-Meteo n'a pas fourni de réponse exploitable."""


class ReponseMeteoInvalide(MeteoErreur):
    """La réponse reçue ne respecte pas le format attendu."""


def valider_coordonnees(latitude, longitude):
    """Retourne des coordonnées finies et dans les limites géographiques."""
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise CoordonneesInvalides("Les coordonnées de la zone sont invalides.")

    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise CoordonneesInvalides("Les coordonnées de la zone sont invalides.")

    return latitude, longitude


def _cache_key(latitude, longitude):
    return f"meteo:v1:{latitude:.6f}:{longitude:.6f}"


def _weather(code):
    if code is None:
        return {"code": None, "description": None, "category": "unknown"}
    if isinstance(code, bool) or not isinstance(code, (int, float)):
        raise ReponseMeteoInvalide("Code météo invalide.")
    if not math.isfinite(code) or int(code) != code:
        raise ReponseMeteoInvalide("Code météo invalide.")

    code = int(code)
    description, category = WMO_WEATHER.get(
        code,
        (f"Code météo Open-Meteo {code} non reconnu", "unknown"),
    )
    return {"code": code, "description": description, "category": category}


def _validate_time(value, date_only=False):
    if not isinstance(value, str) or not value:
        raise ReponseMeteoInvalide("Date ou heure météo invalide.")
    try:
        if date_only:
            date.fromisoformat(value)
        else:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReponseMeteoInvalide("Date ou heure météo invalide.") from exc
    return value


def _numeric_value(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReponseMeteoInvalide("Valeur météo numérique invalide.")
    if not math.isfinite(value):
        raise ReponseMeteoInvalide("Valeur météo numérique invalide.")
    return value


def _normaliser_actuel(data):
    bloc = data.get("current")
    if bloc is None:
        resultat = {"time": None}
        for champ in CURRENT_FIELDS:
            resultat[CURRENT_NAMES[champ]] = (
                {"code": None, "description": None, "category": "unknown"}
                if champ == "weather_code"
                else None
            )
        return resultat
    if not isinstance(bloc, dict):
        raise ReponseMeteoInvalide("Bloc météo actuel invalide.")

    time = bloc.get("time")
    resultat = {"time": _validate_time(time) if time is not None else None}
    for champ in CURRENT_FIELDS:
        valeur = _numeric_value(bloc.get(champ))
        if champ == "weather_code":
            resultat[CURRENT_NAMES[champ]] = _weather(valeur)
        else:
            resultat[CURRENT_NAMES[champ]] = valeur
    return resultat


def _normaliser_serie(data, bloc_nom, champs, noms, date_only=False):
    bloc = data.get(bloc_nom)
    if bloc is None:
        return []
    if (
        not isinstance(bloc, dict)
        or not isinstance(bloc.get("time"), list)
        or not bloc["time"]
    ):
        raise ReponseMeteoInvalide(f"Prévisions {bloc_nom} absentes.")

    times = [_validate_time(value, date_only=date_only) for value in bloc["time"]]
    valeurs = {}
    for champ in champs:
        serie = bloc.get(champ)
        if serie is None:
            valeurs[champ] = [None] * len(times)
        elif not isinstance(serie, list) or len(serie) != len(times):
            raise ReponseMeteoInvalide(f"Série météo {champ} invalide.")
        elif champ in ("sunrise", "sunset"):
            valeurs[champ] = [
                _validate_time(value) if value is not None else None
                for value in serie
            ]
        else:
            valeurs[champ] = [_numeric_value(value) for value in serie]

    resultat = []
    for index, timestamp in enumerate(times):
        ligne = {"time": timestamp}
        for champ in champs:
            valeur = valeurs[champ][index]
            ligne[noms[champ]] = (
                _weather(valeur) if champ == "weather_code" else valeur
            )
        resultat.append(ligne)
    return resultat


def normaliser_reponse(data):
    """Valide et normalise la réponse JSON de l'API Open-Meteo."""
    if not isinstance(data, dict):
        raise ReponseMeteoInvalide("La réponse météo doit être un objet JSON.")
    if data.get("error"):
        raise ReponseMeteoInvalide("Open-Meteo a signalé une erreur.")
    fuseau = data.get("timezone")
    if not isinstance(fuseau, str) or not fuseau:
        raise ReponseMeteoInvalide("Fuseau horaire météo absent.")

    return {
        "timezone": fuseau,
        "retrieved_at": timezone.now().isoformat(),
        "current": _normaliser_actuel(data),
        "hourly": _normaliser_serie(
            data, "hourly", HOURLY_FIELDS, HOURLY_NAMES
        ),
        "daily": _normaliser_serie(
            data, "daily", DAILY_FIELDS, DAILY_NAMES, date_only=True
        ),
        "attribution": {
            "provider": "Open-Meteo",
            "url": "https://open-meteo.com/",
        },
    }


def _fetch(latitude, longitude):
    params = {
        "latitude": f"{latitude:.6f}",
        "longitude": f"{longitude:.6f}",
        "current": ",".join(CURRENT_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "timezone": "auto",
        "forecast_days": FORECAST_DAYS,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    request = Request(
        f"{OPEN_METEO_URL}?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "User-Agent": "BeeFlow/1.0",
        },
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read()
    except HTTPError as exc:
        raise ApiMeteoIndisponible(
            f"Open-Meteo a répondu avec le statut HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ApiMeteoIndisponible(
            "Open-Meteo est temporairement indisponible."
        ) from exc

    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReponseMeteoInvalide(
            "La réponse Open-Meteo n'est pas un JSON valide."
        ) from exc

    return normaliser_reponse(data)


def obtenir_previsions(latitude, longitude, force=False):
    """Retourne les prévisions en cache ou en récupère de nouvelles."""
    latitude, longitude = valider_coordonnees(latitude, longitude)
    key = _cache_key(latitude, longitude)

    if not force:
        cached = cache.get(key)
        if cached is not None:
            return cached

    previsions = _fetch(latitude, longitude)
    cache.set(key, previsions, CACHE_TIMEOUT)
    return previsions
