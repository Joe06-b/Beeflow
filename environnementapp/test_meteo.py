import json
from datetime import datetime, timedelta, timezone as datetime_timezone
from io import BytesIO
from urllib.error import HTTPError, URLError
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .meteo_service import (
    ApiMeteoIndisponible,
    CoordonneesInvalides,
    ReponseMeteoInvalide,
    obtenir_previsions,
    valider_coordonnees,
)
from .models import Environnement


def reponse_open_meteo():
    return {
        "timezone": "Africa/Tunis",
        "current": {
            "time": "2026-11-21T04:00",
            "temperature_2m": 18.5,
            "apparent_temperature": 18.0,
            "relative_humidity_2m": 72,
            "surface_pressure": 1015,
            "visibility": 12000,
            "uv_index": 3.2,
            "wind_speed_10m": 9.2,
            "wind_direction_10m": 140,
            "wind_gusts_10m": 14.0,
            "precipitation": 0.1,
            "rain": 0.1,
            "cloud_cover": 35,
            "weather_code": 61,
            "is_day": 0,
        },
        "hourly": {
            "time": ["2026-11-21T04:00", "2026-11-21T05:00"],
            "temperature_2m": [18.5, 18.0],
            "relative_humidity_2m": [72, 74],
            "surface_pressure": [1015, 1014],
            "visibility": [12000, 11500],
            "uv_index": [3.2, 2.8],
            "precipitation_probability": [30, 40],
            "precipitation": [0.1, 0.2],
            "rain": [0.1, 0.2],
            "weather_code": [61, 63],
            "cloud_cover": [35, 45],
            "wind_speed_10m": [9.2, 10.0],
            "wind_direction_10m": [140, 155],
            "wind_gusts_10m": [14.0, 15.0],
        },
        "daily": {
            "time": ["2026-11-21", "2026-11-22"],
            "temperature_2m_max": [22.0, 19.0],
            "temperature_2m_min": [15.0, 14.0],
            "weather_code": [61, 3],
            "uv_index_max": [4.1, 5.0],
            "precipitation_probability_max": [70, 10],
            "precipitation_sum": [3.2, 0.0],
            "wind_speed_10m_max": [18.0, 12.0],
            "sunrise": ["2026-11-21T06:55", "2026-11-22T06:56"],
            "sunset": ["2026-11-21T17:10", "2026-11-22T17:09"],
        },
    }


def mock_urlopen(request, timeout):
    if timeout != 8:
        raise AssertionError("Le délai HTTP doit rester borné.")
    if request.get_method() != "GET":
        raise AssertionError("Open-Meteo doit être interrogé en GET.")
    return BytesIO(json.dumps(reponse_open_meteo()).encode("utf-8"))


def creer_zone(**overrides):
    valeurs = {
        "nomZone": "Rucher des Fleurs",
        "latitude": 36.82,
        "longitude": 10.21,
        "surface": 2.5,
        "temperature": 24.0,
        "humidite": 50.0,
        "precipitation": 0.0,
        "vitesseVent": 15.0,
    }
    valeurs.update(overrides)
    return Environnement.objects.create(**valeurs)


class MeteoServiceTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_valide_limites_geographiques_et_refuse_valeurs_non_finies(self):
        self.assertEqual(valider_coordonnees(-90, 180), (-90.0, 180.0))
        for latitude, longitude in (
            (90.01, 0),
            (0, -180.01),
            (float("nan"), 0),
            (0, float("inf")),
            ("inconnue", 10),
        ):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(CoordonneesInvalides):
                    valider_coordonnees(latitude, longitude)

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_demande_et_normalise_actuel_previsions_et_fuseau(self, urlopen_mock):
        resultat = obtenir_previsions(36.82, 10.21)

        self.assertEqual(resultat["timezone"], "Africa/Tunis")
        self.assertEqual(resultat["current"]["temperature_c"], 18.5)
        self.assertEqual(
            resultat["current"]["weather"],
            {"code": 61, "description": "Pluie faible", "category": "rain"},
        )
        self.assertEqual(resultat["current"]["is_day"], 0)
        self.assertEqual(resultat["hourly"][1]["time"], "2026-11-21T05:00")
        self.assertEqual(resultat["hourly"][1]["wind_direction_degrees"], 155)
        self.assertEqual(resultat["current"]["surface_pressure_hpa"], 1015)
        self.assertEqual(resultat["current"]["visibility_m"], 12000)
        self.assertEqual(resultat["current"]["uv_index"], 3.2)
        self.assertEqual(resultat["daily"][1]["uv_index_max"], 5.0)
        self.assertEqual(
            resultat["hourly"][0]["precipitation_probability_percent"], 30
        )
        self.assertEqual(resultat["daily"][1]["temperature_max_c"], 19.0)
        self.assertEqual(resultat["daily"][0]["sunrise"], "2026-11-21T06:55")
        self.assertTrue(resultat["retrieved_at"])
        self.assertEqual(resultat["attribution"]["provider"], "Open-Meteo")

        request = urlopen_mock.call_args.args[0]
        query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(query["latitude"], ["36.820000"])
        self.assertEqual(query["longitude"], ["10.210000"])
        self.assertEqual(query["timezone"], ["auto"])
        self.assertEqual(query["forecast_days"], ["7"])
        self.assertIn("apparent_temperature", query["current"][0])
        self.assertIn("surface_pressure", query["current"][0])
        self.assertIn("visibility", query["current"][0])
        self.assertIn("uv_index", query["current"][0])
        self.assertIn("wind_direction_10m", query["hourly"][0])

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_cache_reutilise_les_coordonnees_et_force_un_nouvel_appel(
        self, urlopen_mock
    ):
        instants = (
            datetime(2026, 11, 21, 10, 0, tzinfo=datetime_timezone.utc),
            datetime(2026, 11, 21, 10, 1, tzinfo=datetime_timezone.utc),
        )
        with patch(
            "environnementapp.meteo_service.timezone.now",
            side_effect=instants,
        ):
            premiere = obtenir_previsions(36.82, 10.21)
            seconde = obtenir_previsions(36.82, 10.21)
            forcee = obtenir_previsions(36.82, 10.21, force=True)

        self.assertEqual(urlopen_mock.call_count, 2)
        self.assertEqual(premiere["current"], seconde["current"])
        self.assertEqual(
            premiere["retrieved_at"],
            "2026-11-21T10:00:00+00:00",
        )
        self.assertEqual(
            seconde["retrieved_at"],
            "2026-11-21T10:00:00+00:00",
        )
        self.assertEqual(
            forcee["retrieved_at"],
            "2026-11-21T10:01:00+00:00",
        )
        self.assertNotEqual(premiere["retrieved_at"], forcee["retrieved_at"])

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_coordonnees_invalides_ne_declenchent_aucun_appel(self, urlopen_mock):
        with self.assertRaises(CoordonneesInvalides):
            obtenir_previsions(91, 10)
        urlopen_mock.assert_not_called()

    @patch(
        "environnementapp.meteo_service.urlopen",
        side_effect=URLError("connexion interrompue"),
    )
    def test_erreur_reseau_est_explicite_et_non_mise_en_cache(self, urlopen_mock):
        with self.assertRaises(ApiMeteoIndisponible):
            obtenir_previsions(36.82, 10.21)
        self.assertIsNone(cache.get("meteo:v1:36.820000:10.210000"))
        urlopen_mock.assert_called_once()

    def test_erreurs_http_et_delais_depassees_sont_signales(self):
        erreurs = (
            HTTPError(
                "https://api.open-meteo.com/v1/forecast",
                503,
                "Service Unavailable",
                {},
                None,
            ),
            TimeoutError("délai dépassé"),
        )
        for erreur in erreurs:
            with self.subTest(erreur=type(erreur).__name__):
                cache.clear()
                with patch(
                    "environnementapp.meteo_service.urlopen",
                    side_effect=erreur,
                ):
                    with self.assertRaises(ApiMeteoIndisponible):
                        obtenir_previsions(36.82, 10.21)

    def test_json_invalide_est_signale(self):
        with patch(
            "environnementapp.meteo_service.urlopen",
            return_value=BytesIO(b"ceci n'est pas du JSON"),
        ):
            with self.assertRaises(ReponseMeteoInvalide):
                obtenir_previsions(36.82, 10.21)

    @patch("environnementapp.meteo_service.urlopen")
    def test_series_incoherentes_et_dates_invalides_sont_refusees(self, urlopen_mock):
        payload = reponse_open_meteo()
        payload["hourly"]["temperature_2m"].pop()
        urlopen_mock.return_value = BytesIO(json.dumps(payload).encode("utf-8"))
        with self.assertRaises(ReponseMeteoInvalide):
            obtenir_previsions(36.82, 10.21)

        cache.clear()
        payload = reponse_open_meteo()
        payload["daily"]["time"][0] = "hier"
        urlopen_mock.return_value = BytesIO(json.dumps(payload).encode("utf-8"))
        with self.assertRaises(ReponseMeteoInvalide):
            obtenir_previsions(36.82, 10.21)

    def test_variables_absentes_restent_nulles(self):
        payload = reponse_open_meteo()
        del payload["current"]["apparent_temperature"]
        del payload["hourly"]["precipitation"]
        del payload["hourly"]["wind_direction_10m"]
        with patch(
            "environnementapp.meteo_service.urlopen",
            return_value=BytesIO(json.dumps(payload).encode("utf-8")),
        ):
            resultat = obtenir_previsions(36.82, 10.21)

        self.assertIsNone(resultat["current"]["apparent_temperature_c"])
        self.assertIsNone(resultat["hourly"][0]["precipitation_mm"])
        self.assertIsNone(resultat["hourly"][0]["wind_direction_degrees"])

    def test_blocs_meteo_absents_restent_non_inventes(self):
        payload = reponse_open_meteo()
        payload.pop("current")
        payload.pop("hourly")
        payload.pop("daily")
        with patch(
            "environnementapp.meteo_service.urlopen",
            return_value=BytesIO(json.dumps(payload).encode("utf-8")),
        ):
            resultat = obtenir_previsions(36.82, 10.21)

        self.assertIsNone(resultat["current"]["time"])
        self.assertIsNone(resultat["current"]["temperature_c"])
        self.assertEqual(
            resultat["current"]["weather"],
            {"code": None, "description": None, "category": "unknown"},
        )
        self.assertEqual(resultat["hourly"], [])
        self.assertEqual(resultat["daily"], [])


class MeteoApiFrontofficeTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.zone = creer_zone()

    def test_liste_zones_ne_declenche_pas_de_requete_meteo(self):
        with patch("environnementapp.meteo_service.urlopen") as urlopen_mock:
            response = self.client.get(reverse("environnement:api_zones_meteo"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "zones": [
                    {
                        "id": self.zone.pk,
                        "name": self.zone.nomZone,
                        "latitude": self.zone.latitude,
                        "longitude": self.zone.longitude,
                        "environment": {
                            "vegetation_type": self.zone.typeVegetation,
                            "surface_hectares": self.zone.surface,
                            "bloom_level": self.zone.niveauFloraison,
                            "recorded_measurement": {
                                "temperature_c": self.zone.temperature,
                                "humidity_percent": self.zone.humidite,
                                "precipitation_mm": self.zone.precipitation,
                                "wind_speed_kmh": self.zone.vitesseVent,
                                "measured_at": self.zone.dateMesure.isoformat(),
                            },
                        },
                    }
                ]
            },
        )
        urlopen_mock.assert_not_called()

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_meteo_zone_est_mise_en_cache_sans_modifier_les_mesures(
        self, urlopen_mock
    ):
        url = reverse(
            "environnement:api_meteo_zone",
            kwargs={"pk": self.zone.pk},
        )
        first = self.client.get(url)
        second = self.client.get(url)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first["Cache-Control"], "no-store")
        self.assertEqual(first.json()["status"], "available")
        self.assertEqual(first.json()["zone"]["id"], self.zone.pk)
        self.assertEqual(first.json()["current"]["temperature_c"], 18.5)
        urlopen_mock.assert_called_once()

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.temperature, 24.0)
        self.assertEqual(self.zone.humidite, 50.0)
        self.assertEqual(self.zone.precipitation, 0.0)
        self.assertEqual(self.zone.vitesseVent, 15.0)

    def test_zone_inconnue_et_coordonnees_invalides_ont_des_reponses_json(self):
        missing = self.client.get(
            reverse("environnement:api_meteo_zone", kwargs={"pk": 999999})
        )
        zone_invalide = creer_zone(nomZone="Zone sans coordonnées", latitude=91)
        invalid = self.client.get(
            reverse(
                "environnement:api_meteo_zone",
                kwargs={"pk": zone_invalide.pk},
            )
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["status"], "zone_introuvable")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["status"], "sans_coordonnees")

    def test_erreur_api_est_normalisee_sans_exposer_details(self):
        with patch(
            "environnementapp.meteo_service.urlopen",
            side_effect=URLError("erreur interne non exposée"),
        ):
            response = self.client.get(
                reverse(
                    "environnement:api_meteo_zone",
                    kwargs={"pk": self.zone.pk},
                )
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["status"], "api_indisponible")
        self.assertNotContains(
            response,
            "erreur interne non exposée",
            status_code=502,
        )

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_actualisation_forcee_est_post_et_limitee(
        self, urlopen_mock
    ):
        refresh_url = reverse(
            "environnement:api_actualiser_meteo",
            kwargs={"pk": self.zone.pk},
        )
        first = self.client.post(refresh_url)
        second = self.client.post(refresh_url)
        wrong_method = self.client.get(refresh_url)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json()["status"], "refresh_rate_limited")
        self.assertEqual(second["Retry-After"], "30")
        self.assertEqual(wrong_method.status_code, 405)
        urlopen_mock.assert_called_once()

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_actualisation_forcee_recharge_le_cache(self, urlopen_mock):
        data_url = reverse(
            "environnement:api_meteo_zone",
            kwargs={"pk": self.zone.pk},
        )
        refresh_url = reverse(
            "environnement:api_actualiser_meteo",
            kwargs={"pk": self.zone.pk},
        )
        self.client.get(data_url)
        response = self.client.post(refresh_url)
        self.client.get(data_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(urlopen_mock.call_count, 2)


@override_settings(DEBUG=False)
class MeteoApiBackofficePermissionsTest(TestCase):
    def setUp(self):
        cache.clear()
        self.zone = creer_zone()
        self.client = Client()
        self.urls = (
            reverse("environnement_bo:api_zones_meteo"),
            reverse(
                "environnement_bo:api_meteo_zone",
                kwargs={"pk": self.zone.pk},
            ),
            reverse(
                "environnement_bo:api_actualiser_meteo",
                kwargs={"pk": self.zone.pk},
            ),
        )

    def test_visiteur_non_authentifie_ne_peut_pas_utiliser_les_api_backoffice(
        self,
    ):
        responses = (
            self.client.get(self.urls[0]),
            self.client.get(self.urls[1]),
            self.client.post(self.urls[2]),
        )

        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "authentication_required",
                )

    @override_settings(DEBUG=True)
    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_api_backoffice_est_accessible_sans_authentification_en_developpement(
        self,
        urlopen_mock,
    ):
        zones = self.client.get(self.urls[0])
        meteo = self.client.get(self.urls[1])
        refresh = self.client.post(self.urls[2])

        self.assertEqual(zones.status_code, 200)
        self.assertEqual(meteo.status_code, 200)
        self.assertEqual(refresh.status_code, 200)
        self.assertEqual(urlopen_mock.call_count, 2)

    def test_utilisateur_authentifie_non_staff_est_refuse(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="meteo-user",
            password="test-password",
            is_staff=False,
        )
        self.client.login(username="meteo-user", password="test-password")

        responses = (
            self.client.get(self.urls[0]),
            self.client.get(self.urls[1]),
            self.client.post(self.urls[2]),
        )

        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "permission_denied",
                )

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_membre_staff_peut_consulter_et_actualiser(self, urlopen_mock):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="meteo-admin",
            password="test-password",
            is_staff=True,
        )
        self.client.login(username="meteo-admin", password="test-password")

        zones = self.client.get(self.urls[0])
        meteo = self.client.get(self.urls[1])
        refresh = self.client.post(self.urls[2])

        self.assertEqual(zones.status_code, 200)
        self.assertEqual(zones["Cache-Control"], "private, no-store")
        self.assertEqual(zones.json()["zones"][0]["latitude"], self.zone.latitude)
        self.assertEqual(meteo.status_code, 200)
        self.assertEqual(refresh.status_code, 200)
        self.assertEqual(urlopen_mock.call_count, 2)

    def test_api_backoffice_exige_une_methode_http_adaptee_apres_auth(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="meteo-admin-method",
            password="test-password",
            is_staff=True,
        )
        self.client.login(username="meteo-admin-method", password="test-password")

        response = self.client.post(self.urls[1])

        self.assertEqual(response.status_code, 405)

    @patch("environnementapp.meteo_service.urlopen", side_effect=mock_urlopen)
    def test_actualisation_backoffice_est_limitee(self, urlopen_mock):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="meteo-admin-limit",
            password="test-password",
            is_staff=True,
        )
        self.client.login(username="meteo-admin-limit", password="test-password")

        first = self.client.post(self.urls[2])
        second = self.client.post(self.urls[2])

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        urlopen_mock.assert_called_once()

    def test_actualisation_backoffice_refusee_sans_jeton_csrf(self):
        user_model = get_user_model()
        staff_user = user_model.objects.create_user(
            username="meteo-admin-csrf",
            password="test-password",
            is_staff=True,
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(staff_user)

        response = csrf_client.post(self.urls[2])

        self.assertEqual(response.status_code, 403)
