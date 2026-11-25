from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Environnement


class MeteoPagesTest(TestCase):
    def setUp(self):
        self.zone = Environnement.objects.create(
            nomZone="Rucher des Fleurs",
            latitude=36.82,
            longitude=10.21,
            surface=2.5,
            temperature=24.0,
            humidite=50.0,
            precipitation=0.0,
            vitesseVent=15.0,
        )

    @override_settings(DEBUG=True)
    def test_frontoffice_meteo_page_is_available(self):
        response = self.client.get(reverse("environnement:meteo"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "frontoffice/environnementapp/meteo.html",
        )
        self.assertContains(response, "data-meteo-frontoffice")
        self.assertContains(response, "data-meteo-scene")
        self.assertContains(response, "data-simulation-select")
        self.assertContains(response, "data-value=\"pressure\"")
        self.assertContains(response, "data-value=\"visibility\"")
        self.assertContains(response, "data-value=\"uv\"")
        self.assertContains(response, 'value="snow">Neige')

    @override_settings(DEBUG=False)
    def test_backoffice_meteo_pages_require_staff_access(self):
        list_url = reverse("environnement_bo:meteo")
        detail_url = reverse(
            "environnement_bo:meteo_detail",
            kwargs={"pk": self.zone.pk},
        )

        anonymous_response = self.client.get(list_url)
        self.assertEqual(anonymous_response.status_code, 302)

        user_model = get_user_model()
        user_model.objects.create_user(
            username="meteo-page-user",
            password="test-password",
            is_staff=False,
        )
        self.client.login(username="meteo-page-user", password="test-password")
        self.assertEqual(self.client.get(list_url).status_code, 403)
        self.assertEqual(self.client.get(detail_url).status_code, 403)

        self.client.logout()
        user_model.objects.create_user(
            username="meteo-page-admin",
            password="test-password",
            is_staff=True,
        )
        self.client.login(username="meteo-page-admin", password="test-password")
        list_response = self.client.get(list_url)
        detail_response = self.client.get(detail_url)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotContains(detail_response, "data-simulation-select")
        self.assertTemplateUsed(
            list_response,
            "backoffice/environnementapp/meteo_liste.html",
        )
        self.assertTemplateUsed(
            detail_response,
            "backoffice/environnementapp/meteo_detail.html",
        )

    @override_settings(DEBUG=True)
    def test_environment_backoffice_pages_are_open_in_development(self):
        urls = (
            reverse("environnement_bo:liste"),
            reverse("environnement_bo:ajouter"),
            reverse("environnement_bo:statistiques"),
            reverse("environnement_bo:meteo"),
            reverse("environnement_bo:meteo_detail", kwargs={"pk": self.zone.pk}),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        detail_response = self.client.get(urls[-1])
        self.assertContains(detail_response, "data-simulation-select")

    @override_settings(DEBUG=False)
    def test_frontoffice_and_backoffice_scenarios_are_hidden_outside_debug(self):
        frontoffice = self.client.get(reverse("environnement:meteo"))
        self.assertEqual(frontoffice.status_code, 200)
        self.assertNotContains(frontoffice, "data-simulation-select")

        user_model = get_user_model()
        user_model.objects.create_user(
            username="meteo-production-admin",
            password="test-password",
            is_staff=True,
        )
        self.client.login(
            username="meteo-production-admin",
            password="test-password",
        )
        backoffice = self.client.get(
            reverse(
                "environnement_bo:meteo_detail",
                kwargs={"pk": self.zone.pk},
            )
        )
        self.assertEqual(backoffice.status_code, 200)
        self.assertNotContains(backoffice, "data-simulation-select")

    @override_settings(DEBUG=False)
    def test_legacy_environment_backoffice_still_requires_staff_in_production(self):
        url = reverse("environnement_bo:liste")
        self.assertEqual(self.client.get(url).status_code, 302)

        user_model = get_user_model()
        user_model.objects.create_user(
            username="environment-page-user",
            password="test-password",
            is_staff=False,
        )
        self.client.login(
            username="environment-page-user",
            password="test-password",
        )
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.logout()
        user_model.objects.create_user(
            username="environment-page-admin",
            password="test-password",
            is_staff=True,
        )
        self.client.login(
            username="environment-page-admin",
            password="test-password",
        )
        self.assertEqual(self.client.get(url).status_code, 200)
