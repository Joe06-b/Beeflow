from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import (
    EnvironnementForm,
    RechercheEnvironnementForm,
    StatistiquesEnvironnementForm,
)
from .models import Environnement, NiveauFloraison, NiveauRisque, TypeVegetation
from .services import calculer_statistiques_environnement, filtrer_environnements


def donnees_valides_zone(**overrides):
    donnees = {
        "nomZone": "Zone de test",
        "typeVegetation": TypeVegetation.PRAIRIE,
        "surface": 2.5,
        "latitude": 36.82,
        "longitude": 10.21,
        "temperature": 24.0,
        "humidite": 50.0,
        "precipitation": 0.0,
        "vitesseVent": 15.0,
        "niveauFloraison": NiveauFloraison.MOYENNE,
        "dateMesure": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
    }
    donnees.update(overrides)
    return donnees


class EnvironnementModelTest(TestCase):
    """Tests unitaires du modèle Environnement."""

    def test_creation_environnement_valide(self):
        zone = Environnement.objects.create(
            nomZone="Rucher des Oliviers",
            latitude=36.8065,
            longitude=10.1815,
            typeVegetation=TypeVegetation.VERGER,
            surface=4.5,
            temperature=22.4,
            humidite=55.0,
            precipitation=0.0,
            vitesseVent=12.0,
            niveauFloraison=NiveauFloraison.ABONDANTE,
            dateMesure=timezone.now(),
        )
        self.assertIsNotNone(zone.idZone)
        self.assertEqual(zone.nomZone, "Rucher des Oliviers")
        self.assertEqual(zone.niveauRisque, NiveauRisque.FAIBLE)
        self.assertIsNone(zone.scoreQualite)
        self.assertIn("Rucher des Oliviers", str(zone))

    def test_validation_surface_negative_ou_nulle(self):
        zone = Environnement(
            nomZone="Zone Invalide",
            latitude=36.0,
            longitude=10.0,
            typeVegetation=TypeVegetation.PRAIRIE,
            surface=0.0,
            temperature=20.0,
            humidite=50.0,
            precipitation=0.0,
            vitesseVent=10.0,
            niveauFloraison=NiveauFloraison.MOYENNE,
            dateMesure=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            zone.full_clean()
        self.assertIn("surface", ctx.exception.message_dict)

    def test_validation_coordonnees_invalides(self):
        zone = Environnement(
            nomZone="Pôle Nord fictif",
            latitude=120.0,  # Invalide (> 90)
            longitude=-200.0,  # Invalide (< -180)
            typeVegetation=TypeVegetation.FORET,
            surface=10.0,
            temperature=-5.0,
            humidite=60.0,
            precipitation=5.0,
            vitesseVent=20.0,
            niveauFloraison=NiveauFloraison.ABSENTE,
            dateMesure=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            zone.full_clean()
        self.assertIn("latitude", ctx.exception.message_dict)
        self.assertIn("longitude", ctx.exception.message_dict)

    def test_validation_humidite_invalide(self):
        zone = Environnement(
            nomZone="Humidité impossible",
            latitude=35.0,
            longitude=9.0,
            typeVegetation=TypeVegetation.MAQUIS,
            surface=2.0,
            temperature=30.0,
            humidite=110.0,  # Invalide (> 100%)
            precipitation=0.0,
            vitesseVent=5.0,
            niveauFloraison=NiveauFloraison.FAIBLE,
            dateMesure=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            zone.full_clean()
        self.assertIn("humidite", ctx.exception.message_dict)

    def test_validation_date_future(self):
        zone = Environnement(
            nomZone="Mesure Future",
            latitude=35.0,
            longitude=9.0,
            typeVegetation=TypeVegetation.CULTURE,
            surface=2.0,
            temperature=20.0,
            humidite=50.0,
            precipitation=0.0,
            vitesseVent=5.0,
            niveauFloraison=NiveauFloraison.FAIBLE,
            dateMesure=timezone.now() + timedelta(days=2),  # Invalide (futur)
        )
        with self.assertRaises(ValidationError) as ctx:
            zone.full_clean()
        self.assertIn("dateMesure", ctx.exception.message_dict)


class EnvironnementFormTest(TestCase):
    """Tests du formulaire EnvironnementForm."""

    def test_formulaire_champs_exclus(self):
        form = EnvironnementForm()
        # niveauRisque et scoreQualite ne doivent pas être modifiables dans le formulaire
        self.assertNotIn("niveauRisque", form.fields)
        self.assertNotIn("scoreQualite", form.fields)

    def test_formulaire_valide(self):
        donnees = {
            "nomZone": "Plaine Mellifère",
            "typeVegetation": TypeVegetation.PRAIRIE,
            "surface": 5.2,
            "latitude": 36.75,
            "longitude": 10.22,
            "temperature": 21.5,
            "humidite": 58.0,
            "precipitation": 2.0,
            "vitesseVent": 14.0,
            "niveauFloraison": NiveauFloraison.ABONDANTE,
            "dateMesure": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        }
        form = EnvironnementForm(data=donnees)
        self.assertTrue(form.is_valid(), form.errors)

    def test_widget_date_mesure_utilise_le_format_datetime_local_html(self):
        mesure = timezone.make_aware(datetime(2026, 1, 2, 3, 4))
        form = EnvironnementForm(instance=Environnement(dateMesure=mesure))
        valeur_attendue = timezone.localtime(mesure).strftime("%Y-%m-%dT%H:%M")

        self.assertIn(f'value="{valeur_attendue}"', str(form["dateMesure"]))


@override_settings(DEBUG=True)
class EnvironnementCRUDTest(TestCase):
    """Tests des opérations CRUD du Backoffice."""

    def setUp(self):
        self.client = Client()
        self.zone1 = Environnement.objects.create(
            nomZone="Vallon des Fleurs",
            latitude=36.81,
            longitude=10.19,
            typeVegetation=TypeVegetation.PRAIRIE,
            surface=3.2,
            temperature=23.0,
            humidite=60.0,
            precipitation=0.0,
            vitesseVent=10.0,
            niveauFloraison=NiveauFloraison.ABONDANTE,
            dateMesure=timezone.now() - timedelta(hours=2),
        )

    def test_bo_liste_affiche_zones(self):
        url = reverse("environnement_bo:liste")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/environnementapp/liste.html")
        self.assertContains(response, "Vallon des Fleurs")
        self.assertContains(response, "Prairie")

    def test_bo_detail_affiche_informations(self):
        url = reverse("environnement_bo:detail", kwargs={"pk": self.zone1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/environnementapp/detail.html")
        self.assertContains(response, "Vallon des Fleurs")
        self.assertContains(response, "Conditions météorologiques")
        self.assertContains(response, "23")

    def test_bo_ajouter_zone_succes(self):
        url = reverse("environnement_bo:ajouter")
        # GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/environnementapp/form.html")
        self.assertTemplateUsed(response, "frontoffice/environnementapp/_form_sections.html")
        self.assertTemplateUsed(response, "frontoffice/environnementapp/_regles.html")
        self.assertContains(response, 'id="zone-form"')
        self.assertContains(response, 'name="dateMesure"')

        # POST
        nouvelle_zone = {
            "nomZone": "Colline aux Thyms",
            "typeVegetation": TypeVegetation.MAQUIS,
            "surface": 1.8,
            "latitude": 36.85,
            "longitude": 10.25,
            "temperature": 26.5,
            "humidite": 45.0,
            "precipitation": 0.0,
            "vitesseVent": 18.0,
            "niveauFloraison": NiveauFloraison.MOYENNE,
            "dateMesure": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        }
        post_response = self.client.post(url, data=nouvelle_zone, follow=True)
        self.assertEqual(post_response.status_code, 200)
        created = Environnement.objects.get(nomZone="Colline aux Thyms")
        self.assertContains(post_response, "Colline aux Thyms")
        self.assertContains(post_response, f"Zone #{created.idZone} ajoutée.")

    def test_bo_modifier_zone_succes(self):
        url = reverse("environnement_bo:modifier", kwargs={"pk": self.zone1.pk})
        # GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vallon des Fleurs")

        # POST
        maj_zone = {
            "nomZone": "Vallon des Fleurs Modifié",
            "typeVegetation": TypeVegetation.FORET,
            "surface": 4.0,
            "latitude": 36.81,
            "longitude": 10.19,
            "temperature": 19.5,
            "humidite": 70.0,
            "precipitation": 5.0,
            "vitesseVent": 8.0,
            "niveauFloraison": NiveauFloraison.MOYENNE,
            "dateMesure": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        }
        post_response = self.client.post(url, data=maj_zone, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.zone1.refresh_from_db()
        self.assertEqual(self.zone1.nomZone, "Vallon des Fleurs Modifié")
        self.assertEqual(self.zone1.typeVegetation, TypeVegetation.FORET)
        self.assertContains(post_response, f"Zone #{self.zone1.idZone} modifiée.")

    def test_bo_supprimer_zone_succes(self):
        url = reverse("environnement_bo:supprimer", kwargs={"pk": self.zone1.pk})
        # GET : page de confirmation
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/environnementapp/confirm_delete.html")
        self.assertContains(response, "Supprimer cette zone ?")

        # POST : suppression
        post_response = self.client.post(url, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertFalse(Environnement.objects.filter(pk=self.zone1.pk).exists())
        self.assertContains(post_response, "Aucune zone environnementale enregistrée")
        self.assertContains(post_response, f"Zone #{self.zone1.idZone} supprimée.")

    def test_bo_formulaire_signale_les_erreurs_de_validation(self):
        ajouter = self.client.post(
            reverse("environnement_bo:ajouter"),
            donnees_valides_zone(surface=0),
        )

        modifier = self.client.post(
            reverse("environnement_bo:modifier", kwargs={"pk": self.zone1.pk}),
            donnees_valides_zone(surface=0),
        )

        for response in (ajouter, modifier):
            with self.subTest(path=response.request["PATH_INFO"]):
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "La surface doit être strictement positive")
                self.assertContains(response, "Le formulaire contient des erreurs.")
                self.assertTrue(response.context["form"].is_bound)

    def test_bo_enregistrer_et_ajouter_revient_au_formulaire(self):
        response = self.client.post(
            reverse("environnement_bo:ajouter"),
            donnees_valides_zone(nomZone="Zone suivante", enregistrer_et_ajouter="1"),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.redirect_chain,
            [(reverse("environnement_bo:ajouter"), 302)],
        )
        created = Environnement.objects.get(nomZone="Zone suivante")
        self.assertContains(response, f"Zone #{created.idZone} ajoutée.")

    def test_bo_supprimer_selection_confirme_et_supprime_les_zones(self):
        second = creer_zone("Zone sélectionnée")
        url = reverse("environnement_bo:supprimer_selection")
        ids = [str(self.zone1.pk), str(second.pk)]

        confirmation = self.client.post(url, {"ids": ids})
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, self.zone1.nomZone)
        self.assertContains(confirmation, second.nomZone)

        resultat = self.client.post(
            url,
            {"ids": ids, "confirmer": "1"},
            follow=True,
        )
        self.assertEqual(resultat.status_code, 200)
        self.assertFalse(Environnement.objects.filter(pk__in=ids).exists())
        self.assertContains(resultat, "2 zone(s) supprimée(s).")


class EnvironnementFrontofficeCRUDTest(TestCase):
    """Tests des opérations CRUD du Frontoffice."""

    def setUp(self):
        self.client = Client()
        self.zone1 = Environnement.objects.create(
            nomZone="Vallon des Fleurs",
            latitude=36.81,
            longitude=10.19,
            typeVegetation=TypeVegetation.PRAIRIE,
            surface=3.2,
            temperature=23.0,
            humidite=60.0,
            precipitation=0.0,
            vitesseVent=10.0,
            niveauFloraison=NiveauFloraison.ABONDANTE,
            dateMesure=timezone.now() - timedelta(hours=2),
        )

    def test_fo_liste_affiche_zones(self):
        url = reverse("environnement:liste")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "frontoffice/environnementapp/liste.html")
        self.assertContains(response, "Vallon des Fleurs")
        self.assertContains(response, "Gestion des environnements")
        self.assertContains(response, "Prairie")

    def test_fo_detail_affiche_informations(self):
        url = reverse("environnement:detail", kwargs={"pk": self.zone1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "frontoffice/environnementapp/detail.html")
        self.assertContains(response, "Vallon des Fleurs")
        self.assertContains(response, "Conditions météorologiques")

    def test_fo_ajouter_zone_succes(self):
        url = reverse("environnement:ajouter")
        # GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "frontoffice/environnementapp/form.html")
        for field in (
            "nomZone", "latitude", "longitude", "typeVegetation", "surface",
            "temperature", "humidite", "precipitation", "vitesseVent",
            "niveauFloraison", "dateMesure",
        ):
            self.assertContains(response, f'name="{field}"')

        # POST
        nouvelle_zone = {
            "nomZone": "Plaine du Sud",
            "typeVegetation": TypeVegetation.VERGER,
            "surface": 2.5,
            "latitude": 36.82,
            "longitude": 10.21,
            "temperature": 24.0,
            "humidite": 50.0,
            "precipitation": 0.0,
            "vitesseVent": 15.0,
            "niveauFloraison": NiveauFloraison.MOYENNE,
            "dateMesure": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        }
        post_response = self.client.post(url, data=nouvelle_zone, follow=True)
        self.assertEqual(post_response.status_code, 200)
        created = Environnement.objects.get(nomZone="Plaine du Sud")
        self.assertEqual(
            post_response.redirect_chain,
            [(reverse("environnement:detail", kwargs={"pk": created.pk}), 302)],
        )
        self.assertContains(post_response, f"La zone n°{created.idZone} a été ajoutée avec succès.")

    def test_fo_modifier_zone_succes(self):
        url = reverse("environnement:modifier", kwargs={"pk": self.zone1.pk})
        # GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "frontoffice/environnementapp/form.html")

        # POST
        maj_zone = {
            "nomZone": "Vallon Renouvelé",
            "typeVegetation": TypeVegetation.CULTURE,
            "surface": 5.0,
            "latitude": 36.81,
            "longitude": 10.19,
            "temperature": 22.0,
            "humidite": 55.0,
            "precipitation": 1.0,
            "vitesseVent": 11.0,
            "niveauFloraison": NiveauFloraison.ABONDANTE,
            "dateMesure": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        }
        post_response = self.client.post(url, data=maj_zone, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(
            post_response.redirect_chain,
            [(reverse("environnement:detail", kwargs={"pk": self.zone1.pk}), 302)],
        )
        self.zone1.refresh_from_db()
        self.assertEqual(self.zone1.nomZone, "Vallon Renouvelé")
        self.assertContains(post_response, f"La zone n°{self.zone1.idZone} a été modifiée avec succès.")

    def test_fo_supprimer_zone_succes(self):
        url = reverse("environnement:supprimer", kwargs={"pk": self.zone1.pk})
        # GET : confirmation
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "frontoffice/environnementapp/confirmer_suppression.html")
        self.assertContains(response, "Supprimer la zone « Vallon des Fleurs » ?")

        # POST : suppression
        post_response = self.client.post(url, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(
            post_response.redirect_chain,
            [(reverse("environnement:liste"), 302)],
        )
        self.assertFalse(Environnement.objects.filter(pk=self.zone1.pk).exists())
        self.assertContains(post_response, f"La zone n°{self.zone1.idZone} a été supprimée.")

    def test_fo_formulaire_signale_les_erreurs_de_validation(self):
        ajouter = self.client.post(
            reverse("environnement:ajouter"),
            donnees_valides_zone(surface=0),
        )

        modifier = self.client.post(
            reverse("environnement:modifier", kwargs={"pk": self.zone1.pk}),
            donnees_valides_zone(surface=0),
        )

        for response in (ajouter, modifier):
            with self.subTest(path=response.request["PATH_INFO"]):
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "La surface doit être strictement positive")
                self.assertContains(
                    response,
                    "Le formulaire contient des erreurs. Veuillez les corriger.",
                )
                self.assertTrue(response.context["form"].is_bound)


class IntegriteAutresModulesTest(TestCase):
    """Vérifie que les autres modules et routes restent 100% fonctionnels."""

    def setUp(self):
        self.client = Client()

    def test_accueil_accessible(self):
        response = self.client.get(reverse("accueil"))
        self.assertEqual(response.status_code, 200)

    def test_espace_accessible(self):
        response = self.client.get(reverse("espace"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("environnement:liste"))
        self.assertContains(response, 'href="/environnements/"')

    def test_dashboard_accessible(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)


def creer_zone(nom, veg=TypeVegetation.PRAIRIE, risque=NiveauRisque.FAIBLE, **kw):
    valeurs = dict(
        nomZone=nom, latitude=36.8, longitude=10.2, typeVegetation=veg, surface=2.0,
        temperature=20.0, humidite=50.0, precipitation=0.0, vitesseVent=10.0,
        niveauFloraison=NiveauFloraison.MOYENNE, niveauRisque=risque,
        dateMesure=timezone.now() - timedelta(hours=1),
    )
    valeurs.update(kw)
    return Environnement.objects.create(**valeurs)


@override_settings(DEBUG=True)
class EnvironnementRechercheFiltresTest(TestCase):
    """Recherche, filtres avancés et tris de la liste des environnements."""

    def setUp(self):
        maintenant = timezone.now()
        self.za = creer_zone("Forêt des Cèdres", TypeVegetation.FORET, NiveauRisque.FAIBLE,
                             dateMesure=maintenant - timedelta(days=5), surface=1.0)
        self.zb = creer_zone("Prairie des Abeilles", TypeVegetation.PRAIRIE, NiveauRisque.MOYEN,
                             dateMesure=maintenant - timedelta(days=2), surface=2.0)
        self.zc = creer_zone("Maquis du Soleil", TypeVegetation.MAQUIS, NiveauRisque.ELEVE,
                             dateMesure=maintenant - timedelta(hours=1), surface=3.0)

    def test_formulaire_conserve_les_filtres_et_limite_les_tris_essentiels(self):
        form = RechercheEnvironnementForm()
        self.assertTrue({
            "q", "type_vegetation", "niveau_floraison", "niveau_risque",
            *RechercheEnvironnementForm.FILTRES_AVANCES,
        }.issubset(form.fields))
        self.assertEqual(
            [value for value, _ in form.fields["tri"].choices],
            ["date_desc", "date_asc", "nom_asc", "surface_asc", "surface_desc", "risque_asc"],
        )

    def test_sans_critere_tout_est_retourne_trie_par_date_decroissante(self):
        self.assertEqual(list(filtrer_environnements({})), [self.zc, self.zb, self.za])
        self.assertEqual(list(filtrer_environnements(None)), [self.zc, self.zb, self.za])

    def test_recherche_par_nom(self):
        self.assertEqual(list(filtrer_environnements({"q": "Cèdres"})), [self.za])
        self.assertEqual(list(filtrer_environnements({"q": "prairie"})), [self.zb])
        self.assertEqual(filtrer_environnements({"q": "Inexistant"}).count(), 0)

    def test_filtre_vegetation(self):
        self.assertEqual(list(filtrer_environnements({"type_vegetation": TypeVegetation.FORET})), [self.za])

    def test_filtre_risque(self):
        self.assertEqual(list(filtrer_environnements({"niveau_risque": NiveauRisque.ELEVE})), [self.zc])

    def test_filtre_floraison(self):
        self.zb.niveauFloraison = NiveauFloraison.ABONDANTE
        self.zb.save(update_fields=["niveauFloraison"])
        self.assertEqual(
            list(filtrer_environnements({"niveau_floraison": NiveauFloraison.ABONDANTE})),
            [self.zb],
        )

    def test_filtres_avances_individuels_et_combines(self):
        date_mesure = timezone.now() - timedelta(days=100)
        zone = creer_zone(
            "Cèdre avancé",
            TypeVegetation.FORET,
            NiveauRisque.CRITIQUE,
            surface=8.5,
            temperature=-3.2,
            humidite=35.5,
            precipitation=4.3,
            vitesseVent=14.2,
            niveauFloraison=NiveauFloraison.ABSENTE,
            dateMesure=date_mesure,
        )
        filtres_individuels = [
            {"surface_min": 8.5, "surface_max": 8.5},
            {"temperature_min": -3.2, "temperature_max": -3.2},
            {"humidite_min": 35.5, "humidite_max": 35.5},
            {"precipitation_min": 4.3, "precipitation_max": 4.3},
            {"vitesseVent_min": 14.2, "vitesseVent_max": 14.2},
            {
                "date_debut": date_mesure.date(),
                "date_fin": date_mesure.date(),
            },
        ]
        for filtres in filtres_individuels:
            with self.subTest(filtres=filtres):
                self.assertEqual(list(filtrer_environnements(filtres)), [zone])

        filtres_combines = {
            "q": "Cèdre",
            "type_vegetation": TypeVegetation.FORET,
            "niveau_floraison": NiveauFloraison.ABSENTE,
            "niveau_risque": NiveauRisque.CRITIQUE,
            "surface_min": 8.5,
            "temperature_max": -3.2,
            "humidite_min": 35.5,
            "precipitation_min": 4.3,
            "vitesseVent_max": 14.2,
            "date_debut": date_mesure.date(),
            "date_fin": date_mesure.date(),
        }
        self.assertEqual(list(filtrer_environnements(filtres_combines)), [zone])

    def test_chaque_tri_essentiel(self):
        tris_attendus = {
            "date_desc": [self.zc, self.zb, self.za],
            "date_asc": [self.za, self.zb, self.zc],
            "nom_asc": [self.za, self.zc, self.zb],
            "surface_asc": [self.za, self.zb, self.zc],
            "surface_desc": [self.zc, self.zb, self.za],
            "risque_asc": [self.za, self.zb, self.zc],
        }
        for tri, attendus in tris_attendus.items():
            with self.subTest(tri=tri):
                self.assertEqual(list(filtrer_environnements({"tri": tri})), attendus)

    def test_filtres_combines(self):
        res = filtrer_environnements({"q": "des", "type_vegetation": TypeVegetation.PRAIRIE,
                                      "niveau_risque": NiveauRisque.MOYEN})
        self.assertEqual(list(res), [self.zb])
        res = filtrer_environnements({"q": "des", "niveau_risque": NiveauRisque.ELEVE})
        self.assertEqual(res.count(), 0)

    def test_vue_bo_recherche_et_filtres(self):
        response = self.client.get(reverse("environnement_bo:liste"), {"q": "Cèdres", "type_vegetation": "Foret"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forêt des Cèdres")
        self.assertNotContains(response, "Prairie des Abeilles")

    def test_vue_fo_recherche_et_filtres(self):
        response = self.client.get(reverse("environnement:liste"), {"niveau_risque": "Moyen"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prairie des Abeilles")
        self.assertNotContains(response, "Maquis du Soleil")

    def test_vue_fo_filtre_invalide_ne_plante_pas(self):
        response = self.client.get(reverse("environnement:liste"), {"type_vegetation": "N'importe quoi"})
        self.assertEqual(response.status_code, 200)

    def test_pages_exposent_les_filtres_et_ouvrent_les_filtres_avances_actifs(self):
        for nom in ("environnement:liste", "environnement_bo:liste"):
            response = self.client.get(reverse(nom), {"surface_min": "0"})
            html = response.content.decode()
            self.assertEqual(response.status_code, 200)
            for champ in (
                "niveau_floraison",
                "niveau_risque",
                "surface_min",
                "temperature_min",
                "humidite_min",
                "precipitation_min",
                "vitesseVent_min",
                "date_debut",
                "name=\"tri\"",
            ):
                self.assertIn(champ, html)
            self.assertIn('<details class="env-advanced" open>', html)

    def test_vues_frontoffice_et_backoffice_combinent_les_filtres(self):
        date_mesure = timezone.now() - timedelta(days=100)
        zone = creer_zone(
            "Cèdre filtré",
            TypeVegetation.FORET,
            NiveauRisque.CRITIQUE,
            surface=8.5,
            temperature=-3.2,
            humidite=35.5,
            precipitation=4.3,
            vitesseVent=14.2,
            niveauFloraison=NiveauFloraison.ABSENTE,
            dateMesure=date_mesure,
        )
        params = {
            "q": "Cèdre",
            "type_vegetation": TypeVegetation.FORET,
            "niveau_floraison": NiveauFloraison.ABSENTE,
            "niveau_risque": NiveauRisque.CRITIQUE,
            "surface_min": "8.5",
            "temperature_max": "-3.2",
            "humidite_min": "35.5",
            "precipitation_min": "4.3",
            "vitesseVent_max": "14.2",
            "date_debut": date_mesure.date().isoformat(),
            "date_fin": date_mesure.date().isoformat(),
        }
        for route in ("environnement:liste", "environnement_bo:liste"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route), params)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, zone.nomZone)
                self.assertNotContains(response, "Forêt des Cèdres")


@override_settings(DEBUG=True)
class EnvironnementExportCSVTest(TestCase):
    """L'export CSV doit contenir toutes les lignes filtrées, pas seulement la page affichée."""

    URL = "environnement_bo:export_csv"

    def lignes(self, response):
        texte = response.content.decode("utf-8-sig")
        return [l for l in texte.split("\r\n") if l]

    def test_base_vide_en_tete_seul(self):
        response = self.client.get(reverse(self.URL))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.lignes(response)), 1)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_toutes_les_lignes_au_dela_d_une_page(self):
        for n in range(25):  # PAR_PAGE = 10 -> 3 pages
            creer_zone(f"Zone {n:02d}")
        lignes = self.lignes(self.client.get(reverse(self.URL), {"page": "2"}))
        self.assertEqual(len(lignes), 1 + 25)

    def test_export_respecte_les_filtres(self):
        for n in range(12):
            creer_zone(f"Verger {n}", TypeVegetation.VERGER, NiveauRisque.ELEVE)
        for n in range(5):
            creer_zone(f"Foret {n}", TypeVegetation.FORET, NiveauRisque.FAIBLE)
        r = self.client.get(reverse(self.URL), {"type_vegetation": "Verger", "niveau_risque": "Eleve"})
        self.assertEqual(len(self.lignes(r)), 1 + 12)
        r = self.client.get(reverse(self.URL), {"q": "foret"})
        self.assertEqual(len(self.lignes(r)), 1 + 5)
        r = self.client.get(reverse(self.URL), {"q": "zzz"})
        self.assertEqual(len(self.lignes(r)), 1)

    def test_export_respecte_filtres_avances_combines_sur_toutes_les_pages(self):
        date_mesure = timezone.now() - timedelta(days=100)
        attendues = [
            creer_zone(
                f"Cèdre {n}",
                TypeVegetation.FORET,
                NiveauRisque.CRITIQUE,
                surface=8.5,
                temperature=-3.2,
                humidite=35.5,
                precipitation=4.3,
                vitesseVent=14.2,
                niveauFloraison=NiveauFloraison.ABSENTE,
                dateMesure=date_mesure,
            )
            for n in range(12)
        ]
        creer_zone(
            "Cèdre exclu",
            TypeVegetation.FORET,
            NiveauRisque.FAIBLE,
            surface=8.5,
            temperature=-3.2,
            humidite=35.5,
            precipitation=4.3,
            vitesseVent=14.2,
            niveauFloraison=NiveauFloraison.ABSENTE,
            dateMesure=date_mesure,
        )
        params = {
            "q": "Cèdre",
            "type_vegetation": TypeVegetation.FORET,
            "niveau_floraison": NiveauFloraison.ABSENTE,
            "niveau_risque": NiveauRisque.CRITIQUE,
            "surface_min": "8.5",
            "surface_max": "8.5",
            "temperature_min": "-3.2",
            "temperature_max": "-3.2",
            "humidite_min": "35.5",
            "humidite_max": "35.5",
            "precipitation_min": "4.3",
            "precipitation_max": "4.3",
            "vitesseVent_min": "14.2",
            "vitesseVent_max": "14.2",
            "date_debut": date_mesure.date().isoformat(),
            "date_fin": date_mesure.date().isoformat(),
            "page": "2",
        }

        response = self.client.get(reverse(self.URL), params)
        lignes = self.lignes(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(lignes), 1 + len(attendues))
        for zone in attendues:
            self.assertTrue(any(f";{zone.nomZone};" in ligne for ligne in lignes[1:]))

    def test_pagination_conserve_les_filtres_et_ignore_le_numero_de_page_dans_les_params(self):
        for n in range(25):
            creer_zone(f"Prairie {n:02d}", TypeVegetation.PRAIRIE)

        response = self.client.get(
            reverse("environnement_bo:liste"),
            {"type_vegetation": TypeVegetation.PRAIRIE, "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page"].number, 2)
        self.assertEqual(
            response.context["params"],
            f"type_vegetation={TypeVegetation.PRAIRIE}",
        )
        self.assertRegex(
            response.content.decode(),
            r'href="\?type_vegetation=Prairie(?:&amp;|&)page=1"',
        )

    def test_export_avec_formulaire_complet_vide_comme_le_navigateur(self):
        creer_zone("Zone é")
        r = self.client.get(reverse(self.URL) + "?q=&type_vegetation=&niveau_risque=")
        self.assertEqual(len(self.lignes(r)), 2)

    def test_contenu_des_colonnes(self):
        z = creer_zone("Rucher é;test", TypeVegetation.VERGER, NiveauRisque.ELEVE, scoreQualite=0.0)
        lignes = self.lignes(self.client.get(reverse(self.URL)))
        self.assertEqual(
            lignes[0],
            "ID;Nom de la zone;Type de végétation;Surface (ha);Latitude;Longitude;"
            "Température (°C);Humidité (%);Précipitations (mm);Vitesse vent (km/h);"
            "Niveau floraison;Date mesure;Niveau risque;Score qualité",
        )
        ligne = lignes[1]
        self.assertTrue(ligne.startswith(f"{z.idZone};"))
        self.assertIn('"Rucher é;test"', ligne)   # le point-virgule est bien protégé
        self.assertIn(";Verger;", ligne)
        self.assertIn(";Élevé;0.0", ligne)        # un score de 0 n'est plus affiché vide


@override_settings(DEBUG=True)
class EnvironnementStatistiquesTest(TestCase):
    """Calculs et affichage des statistiques filtrées du Backoffice."""

    def setUp(self):
        self.jour_un = timezone.make_aware(datetime(2026, 1, 10, 10, 0))
        self.jour_deux = timezone.make_aware(datetime(2026, 1, 11, 10, 0))
        self.zone_foret = creer_zone(
            "Forêt statistique",
            TypeVegetation.FORET,
            NiveauRisque.FAIBLE,
            surface=1.0,
            temperature=20.0,
            humidite=40.0,
            precipitation=0.0,
            niveauFloraison=NiveauFloraison.ABSENTE,
            dateMesure=self.jour_un,
        )
        self.zone_prairie = creer_zone(
            "Prairie statistique",
            TypeVegetation.PRAIRIE,
            NiveauRisque.MOYEN,
            surface=3.0,
            temperature=30.0,
            humidite=60.0,
            precipitation=4.0,
            niveauFloraison=NiveauFloraison.FAIBLE,
            dateMesure=self.jour_un + timedelta(hours=2),
        )
        self.zone_verger = creer_zone(
            "Verger statistique",
            TypeVegetation.VERGER,
            NiveauRisque.ELEVE,
            surface=6.0,
            temperature=10.0,
            humidite=80.0,
            precipitation=2.0,
            niveauFloraison=NiveauFloraison.ABONDANTE,
            dateMesure=self.jour_deux,
        )

    def test_formulaire_valide_les_cinq_filtres_et_l_intervalle(self):
        form = StatistiquesEnvironnementForm(data={
            "type_vegetation": TypeVegetation.FORET,
            "niveau_floraison": NiveauFloraison.ABSENTE,
            "niveau_risque": NiveauRisque.FAIBLE,
            "date_debut": "2026-01-10",
            "date_fin": "2026-01-11",
        })
        self.assertTrue(form.is_valid(), form.errors)

        intervalle_inverse = StatistiquesEnvironnementForm(data={
            "date_debut": "2026-01-11",
            "date_fin": "2026-01-10",
        })
        self.assertFalse(intervalle_inverse.is_valid())
        self.assertIn("date_fin", intervalle_inverse.errors)

    def test_kpi_et_repartitions_sont_calcules_depuis_les_zones(self):
        stats, graphiques = calculer_statistiques_environnement()

        self.assertEqual(stats, {
            "total": 3,
            "surface_totale": 10.0,
            "temperature_moyenne": 20.0,
            "humidite_moyenne": 60.0,
            "precipitation_moyenne": 2.0,
            "types_vegetation": 3,
        })
        self.assertEqual(graphiques["vegetation"]["data"], [1, 1, 0, 1, 0, 0])
        self.assertEqual(
            graphiques["floraison"]["labels"],
            [label for _, label in NiveauFloraison.choices],
        )
        self.assertEqual(graphiques["floraison"]["data"], [1, 1, 0, 1])
        self.assertEqual(
            graphiques["risque"]["labels"],
            [label for _, label in NiveauRisque.choices],
        )
        self.assertEqual(graphiques["risque"]["data"], [1, 1, 1, 0])

    def test_evolution_agrege_les_mesures_de_la_meme_date(self):
        _, graphiques = calculer_statistiques_environnement()
        evolution = graphiques["evolution"]

        self.assertTrue(evolution["disponible"])
        self.assertEqual(evolution["labels"], ["10/01/2026", "11/01/2026"])
        self.assertEqual(evolution["temperature"], [25.0, 10.0])
        self.assertEqual(evolution["humidite"], [50.0, 80.0])

    def test_filtres_statistiques_individuels(self):
        cas = [
            ({"type_vegetation": TypeVegetation.FORET}, 1),
            ({"niveau_floraison": NiveauFloraison.FAIBLE}, 1),
            ({"niveau_risque": NiveauRisque.MOYEN}, 1),
            ({"date_debut": self.jour_deux.date()}, 1),
            ({"date_fin": self.jour_un.date()}, 2),
        ]
        for filtres, total_attendu in cas:
            with self.subTest(filtres=filtres):
                stats, _ = calculer_statistiques_environnement(filtres)
                self.assertEqual(stats["total"], total_attendu)

    def test_filtres_combines_actualisent_tous_les_kpi_et_graphiques(self):
        filtres = {
            "type_vegetation": TypeVegetation.FORET,
            "niveau_floraison": NiveauFloraison.ABSENTE,
            "niveau_risque": NiveauRisque.FAIBLE,
            "date_debut": self.jour_un.date(),
            "date_fin": self.jour_un.date(),
        }
        stats, graphiques = calculer_statistiques_environnement(filtres)

        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["surface_totale"], 1.0)
        self.assertEqual(stats["temperature_moyenne"], 20.0)
        self.assertEqual(stats["humidite_moyenne"], 40.0)
        self.assertEqual(stats["precipitation_moyenne"], 0.0)
        self.assertEqual(stats["types_vegetation"], 1)
        self.assertEqual(graphiques["vegetation"]["data"], [1, 0, 0, 0, 0, 0])
        self.assertEqual(graphiques["floraison"]["data"], [1, 0, 0, 0])
        self.assertEqual(graphiques["risque"]["data"], [1, 0, 0, 0])
        self.assertFalse(graphiques["evolution"]["disponible"])

    def test_vue_affiche_six_kpi_quatre_graphiques_et_onglet_actif(self):
        response = self.client.get(reverse("environnement_bo:statistiques"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "backoffice/environnementapp/statistiques.html",
        )
        html = response.content.decode()
        self.assertEqual(html.count('<div class="kpi">'), 6)
        self.assertEqual(html.count('class="panel env-stat-chart"'), 4)
        self.assertEqual(html.count("<canvas "), 4)
        self.assertContains(
            response,
            'aria-current="page"',
        )
        self.assertContains(response, "Statistiques")

    def test_vue_conserve_les_filtres_et_affiche_un_message_si_evolution_insuffisante(self):
        response = self.client.get(
            reverse("environnement_bo:statistiques"),
            {
                "type_vegetation": TypeVegetation.FORET,
                "date_debut": "2026-01-10",
                "date_fin": "2026-01-10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total"], 1)
        self.assertEqual(
            response.context["form"]["type_vegetation"].value(),
            TypeVegetation.FORET,
        )
        self.assertContains(response, "Les données filtrées ne couvrent pas")
        self.assertEqual(response.content.decode().count("<canvas "), 3)

    def test_base_vide_affiche_six_kpi_quatre_emplacements_et_aucune_moyenne_fausse(self):
        Environnement.objects.all().delete()
        stats, graphiques = calculer_statistiques_environnement()
        response = self.client.get(reverse("environnement_bo:statistiques"))

        self.assertEqual(stats["total"], 0)
        self.assertIsNone(stats["surface_totale"])
        self.assertIsNone(stats["temperature_moyenne"])
        self.assertIsNone(stats["humidite_moyenne"])
        self.assertIsNone(stats["precipitation_moyenne"])
        self.assertFalse(graphiques["evolution"]["disponible"])
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(html.count('<div class="kpi">'), 6)
        self.assertEqual(html.count('class="panel env-stat-chart"'), 4)
        self.assertIn("Aucune zone ne correspond", html)
        self.assertNotIn("{{ stats.", html)
        self.assertNotIn("{% else", html)
        self.assertNotIn("{% endif", html)