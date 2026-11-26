from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader

from .forms import RucheForm
from .models import ActionHistorique, EtatPredit, HistoriqueRuche, Ruche


@override_settings(ROOT_URLCONF="rucheapp.test_urls")
class RucheCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ruche = Ruche.objects.create(
            code_ruche="R-001",
            type_ruche="Dadant",
            race_abeilles="Buckfast",
            date_installation=date(2025, 5, 10),
            presence_reine=True,
            nombre_abeilles=45_000,
            etat_predit=EtatPredit.BON,
        )

    def test_liste_affiche_la_ruche(self):
        response = self.client.get(reverse("ruches:liste"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R-001")
        self.assertContains(response, "Gestion des ruches")
        self.assertContains(response, "rch-state-bon")
        self.assertNotContains(response, "rch-kpis")
        self.assertNotContains(
            response,
            "Les actions ouvrent le détail, la modification ou la suppression.",
        )

    def test_couleurs_reine_et_etats_du_tableau(self):
        Ruche.objects.create(
            code_ruche="R-ROUGE",
            type_ruche="Dadant",
            race_abeilles="Italienne",
            date_installation=date.today(),
            presence_reine=False,
            nombre_abeilles=12_000,
            etat_predit=EtatPredit.RISQUE_ELEVE,
        )
        Ruche.objects.create(
            code_ruche="R-JAUNE",
            type_ruche="Warre",
            race_abeilles="Noire",
            date_installation=date.today(),
            presence_reine=True,
            nombre_abeilles=18_000,
            etat_predit=EtatPredit.A_SURVEILLER,
        )
        response = self.client.get(reverse("ruches:liste"))
        self.assertContains(response, "rch-state-risque")
        self.assertContains(response, "rch-state-surveillance")
        self.assertContains(response, 'badge is-bad', html=False)

    def test_recherche_et_filtre(self):
        response = self.client.get(reverse("ruches:liste"), {"q": "Buck", "etat": EtatPredit.BON})
        self.assertContains(response, "R-001")

        response = self.client.get(reverse("ruches:liste"), {"q": "introuvable"})
        self.assertNotContains(response, "R-001")

    def test_filtres_et_tris_fonctionnent_dans_le_front_et_le_back(self):
        Ruche.objects.create(
            code_ruche="R-002",
            type_ruche="Warre",
            race_abeilles="Noire",
            date_installation=date(2025, 6, 15),
            presence_reine=False,
            nombre_abeilles=20_000,
            etat_predit=EtatPredit.RISQUE_ELEVE,
        )
        Ruche.objects.create(
            code_ruche="R-003",
            type_ruche="Langstroth",
            race_abeilles="Italienne",
            date_installation=date(2025, 7, 20),
            presence_reine=True,
            nombre_abeilles=30_000,
            etat_predit=EtatPredit.A_SURVEILLER,
        )

        for route in ("ruches:liste", "ruches_front:liste"):
            par_type = self.client.get(reverse(route), {"type": "Warre"})
            self.assertContains(par_type, "R-002")
            self.assertNotContains(par_type, "R-001")
            self.assertEqual(par_type.context["filtres"]["type"], "Warre")

            par_etat = self.client.get(reverse(route), {"etat": EtatPredit.A_SURVEILLER})
            self.assertContains(par_etat, "R-003")
            self.assertNotContains(par_etat, "R-002")
            self.assertEqual(par_etat.context["filtres"]["etat"], EtatPredit.A_SURVEILLER)

            tries = self.client.get(reverse(route), {"tri": "population"})
            codes = [ruche.code_ruche for ruche in tries.context["ruches"]]
            self.assertEqual(codes, ["R-002", "R-003", "R-001"])

            filtre_combine = self.client.get(
                reverse(route),
                {"q": "Ital", "type": "Langstroth", "etat": EtatPredit.A_SURVEILLER},
            )
            self.assertContains(filtre_combine, "R-003")
            self.assertNotContains(filtre_combine, "R-001")

    def test_parametres_de_filtre_invalides_sont_ignores(self):
        for route in ("ruches:liste", "ruches_front:liste"):
            response = self.client.get(
                reverse(route),
                {"type": "inconnu", "etat": "inconnu", "tri": "inconnu"},
            )
            self.assertContains(response, "R-001")
            self.assertEqual(response.context["filtres"]["type"], "")
            self.assertEqual(response.context["filtres"]["etat"], "")
            self.assertEqual(response.context["filtres"]["tri"], "code")

    def test_detail_affiche_les_informations(self):
        response = self.client.get(reverse("ruches:detail", args=[self.ruche.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "45000", html=False)

    def test_creation_normalise_le_code(self):
        response = self.client.post(
            reverse("ruches:ajouter"),
            {
                "code_ruche": "r-002",
                "type_ruche": "Warre",
                "race_abeilles": "Noire",
                "date_installation": date.today().isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 30_000,
                "etat_predit": EtatPredit.A_SURVEILLER,
                "user": "",
                "idZone": "",
            },
        )
        self.assertRedirects(response, reverse("ruches:liste"))
        self.assertTrue(Ruche.objects.filter(code_ruche="R-002").exists())
        historique = HistoriqueRuche.objects.get(code_ruche="R-002")
        self.assertEqual(historique.action, ActionHistorique.AJOUT)
        self.assertEqual(historique.donnees["nombre_abeilles"], 30_000)

    def test_modification(self):
        response = self.client.post(
            reverse("ruches:modifier", args=[self.ruche.pk]),
            {
                "code_ruche": "R-001",
                "type_ruche": "Langstroth",
                "race_abeilles": "Buckfast",
                "date_installation": self.ruche.date_installation.isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 50_000,
                "etat_predit": EtatPredit.BON,
                "user": "",
                "idZone": "",
            },
        )
        self.assertRedirects(response, reverse("ruches:liste"))
        self.ruche.refresh_from_db()
        self.assertEqual(self.ruche.type_ruche, "Langstroth")
        historique = HistoriqueRuche.objects.get(
            code_ruche="R-001",
            action=ActionHistorique.MODIFICATION,
        )
        self.assertIn("type_ruche", historique.changements)
        self.assertEqual(historique.changements["type_ruche"]["avant"], "Dadant")
        self.assertEqual(historique.changements["type_ruche"]["apres"], "Langstroth")

    def test_code_ruche_est_verrouille_pendant_la_modification(self):
        formulaire = RucheForm(instance=self.ruche)
        self.assertTrue(formulaire.fields["code_ruche"].disabled)

        response = self.client.post(
            reverse("ruches:modifier", args=[self.ruche.pk]),
            {
                "code_ruche": "R-CODE-CHANGE",
                "type_ruche": "Dadant",
                "race_abeilles": "Buckfast",
                "date_installation": self.ruche.date_installation.isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 45_000,
                "etat_predit": EtatPredit.BON,
                "user": "",
                "idZone": "",
            },
        )
        self.assertRedirects(response, reverse("ruches:liste"))
        self.ruche.refresh_from_db()
        self.assertEqual(self.ruche.code_ruche, "R-001")

    def test_suppression_exige_un_post(self):
        response = self.client.get(reverse("ruches:supprimer", args=[self.ruche.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Ruche.objects.filter(pk=self.ruche.pk).exists())

        response = self.client.post(reverse("ruches:supprimer", args=[self.ruche.pk]))
        self.assertRedirects(response, reverse("ruches:liste"))
        self.assertFalse(Ruche.objects.filter(pk=self.ruche.pk).exists())
        historique = HistoriqueRuche.objects.get(
            code_ruche="R-001",
            action=ActionHistorique.SUPPRESSION,
        )
        self.assertIsNone(historique.ruche)
        self.assertEqual(historique.donnees["race_abeilles"], "Buckfast")

    def test_modification_sans_changement_ne_cree_pas_historique(self):
        response = self.client.post(
            reverse("ruches:modifier", args=[self.ruche.pk]),
            {
                "code_ruche": "R-001",
                "type_ruche": "Dadant",
                "race_abeilles": "Buckfast",
                "date_installation": self.ruche.date_installation.isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 45_000,
                "etat_predit": EtatPredit.BON,
                "user": "",
                "idZone": "",
            },
        )
        self.assertRedirects(response, reverse("ruches:liste"))
        self.assertFalse(HistoriqueRuche.objects.exists())

    def test_page_historique_filtre_par_ruche_et_action(self):
        HistoriqueRuche.enregistrer(
            self.ruche,
            ActionHistorique.AJOUT,
            apres=self.ruche.valeurs_historiques(),
            auteur="Apiculteur test",
        )
        response = self.client.get(
            reverse("ruches:historique"),
            {"q": "R-001", "action": ActionHistorique.AJOUT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R-001")
        self.assertContains(response, "Apiculteur test")
        self.assertContains(response, "La ruche a été ajoutée")
        self.assertContains(response, "data-ruches-filters", html=False)
        self.assertContains(response, "data-ruches-filter", html=False)

    def test_suppression_d_une_entree_historique_exige_un_post(self):
        entree = HistoriqueRuche.enregistrer(
            self.ruche,
            ActionHistorique.AJOUT,
            apres=self.ruche.valeurs_historiques(),
        )
        url = reverse("ruches:supprimer_historique", args=[entree.pk])

        confirmation = self.client.get(url)
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Supprimer cette entrée")
        self.assertTrue(HistoriqueRuche.objects.filter(pk=entree.pk).exists())

        suppression = self.client.post(url)
        self.assertRedirects(suppression, reverse("ruches:historique"))
        self.assertFalse(HistoriqueRuche.objects.filter(pk=entree.pk).exists())

    def test_statistiques_affichent_les_indicateurs(self):
        response = self.client.get(reverse("ruches:statistiques"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Statistiques")
        self.assertEqual(response.context["stats"]["total"], 1)
        self.assertEqual(response.context["stats"]["nb_bon"], 1)

    def test_formulaire_utilise_des_listes_de_choix(self):
        response = self.client.get(reverse("ruches:ajouter"))
        self.assertContains(response, '<select name="type_ruche"', html=False)
        self.assertContains(response, '<select name="race_abeilles"', html=False)
        self.assertContains(response, 'id="rch-validation-rules"', html=False)

    def test_frontoffice_liste_les_ruches_en_cartes(self):
        response = self.client.get(reverse("ruches_front:liste"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R-001")
        self.assertContains(response, "Dadant")
        self.assertContains(response, 'class="rf-grid"', html=False)
        self.assertContains(response, "Voir les détails")
        self.assertContains(response, "rf-photo-dadant")
        self.assertContains(response, "Ruches affichées")
        self.assertNotContains(response, "data-hive-stage", html=False)
        self.assertContains(
            response,
            reverse("ruches_front:qr", args=[self.ruche.pk]),
        )
        self.assertContains(response, 'class="rf-scan-grid"', html=False)

    def test_qr_frontoffice_affiche_telecharge_et_pointe_vers_le_detail(self):
        with patch("rucheapp.views.adresse_ipv4_locale", return_value="192.168.1.25"):
            page_qr = self.client.get(
                reverse("ruches_front:qr", args=[self.ruche.pk]),
                HTTP_HOST="localhost:8000",
            )
        self.assertEqual(page_qr.status_code, 200)
        self.assertContains(page_qr, "Code QR de R-001")
        self.assertContains(page_qr, "Télécharger")
        self.assertContains(page_qr, "Enregistrer le QR code (PNG)")
        self.assertContains(page_qr, "Imprimer")
        self.assertContains(page_qr, "Générer une étiquette QR")
        self.assertNotContains(page_qr, "<dt>Type</dt>", html=False)
        self.assertNotContains(page_qr, "<dt>Population</dt>", html=False)
        self.assertEqual(
            page_qr.context["qr_target_url"],
            f"http://192.168.1.25:8000{reverse('ruches_front:scan_detail_token', args=[self.ruche.qr_token])}",
        )

        fiche_scan_stable = self.client.get(
            reverse("ruches_front:scan_detail_token", args=[self.ruche.qr_token])
        )
        self.assertEqual(fiche_scan_stable.status_code, 200)
        self.assertContains(fiche_scan_stable, "R-001")

        # L'ancien lien numerique reste valide pour les QR deja imprimes.
        fiche_scan = self.client.get(reverse("ruches_front:scan_detail", args=[self.ruche.pk]))
        self.assertEqual(fiche_scan.status_code, 200)
        self.assertContains(fiche_scan, "Informations de la ruche")
        self.assertContains(fiche_scan, "R-001")
        self.assertContains(fiche_scan, "Buckfast")
        self.assertContains(fiche_scan, "45000 abeilles")
        self.assertNotContains(fiche_scan, 'class="front-header"', html=False)
        self.assertNotContains(fiche_scan, 'class="front-footer"', html=False)

        with patch("rucheapp.views.adresse_ipv4_locale", return_value="192.168.1.25"):
            image_qr = self.client.get(
                reverse("ruches_front:qr_image", args=[self.ruche.pk]),
                HTTP_HOST="localhost:8000",
            )
        self.assertEqual(image_qr.status_code, 200)
        self.assertEqual(image_qr["Content-Type"], "image/png")
        self.assertTrue(image_qr.content.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn("inline", image_qr["Content-Disposition"])

        telechargement = self.client.get(
            reverse("ruches_front:qr_image", args=[self.ruche.pk]),
            {"download": "1"},
        )
        self.assertIn("attachment", telechargement["Content-Disposition"])
        self.assertIn("QR-R-001.png", telechargement["Content-Disposition"])

    @override_settings(BEEFLOW_QR_BASE_URL="https://ruches.beeflow.example")
    def test_qr_utilise_le_domaine_public_configure(self):
        page_qr = self.client.get(reverse("ruches_front:qr", args=[self.ruche.pk]))
        self.assertEqual(
            page_qr.context["qr_target_url"],
            "https://ruches.beeflow.example"
            + reverse("ruches_front:scan_detail_token", args=[self.ruche.qr_token]),
        )

    def test_frontoffice_kpis_suivent_les_etats_reels(self):
        Ruche.objects.create(
            code_ruche="R-RISQUE",
            type_ruche="Langstroth",
            race_abeilles="Italienne",
            date_installation=date.today(),
            presence_reine=True,
            nombre_abeilles=12_000,
            etat_predit=EtatPredit.RISQUE_ELEVE,
        )
        Ruche.objects.create(
            code_ruche="R-SURVEILLANCE",
            type_ruche="Warre",
            race_abeilles="Noire",
            date_installation=date.today(),
            presence_reine=True,
            nombre_abeilles=10_000,
            etat_predit=EtatPredit.A_SURVEILLER,
        )
        response = self.client.get(reverse("ruches_front:liste"))
        self.assertEqual(response.context["nb_bon"], 1)
        self.assertEqual(response.context["nb_surveillance"], 1)
        self.assertEqual(response.context["nb_risque"], 1)
        self.assertContains(response, "Risque élevé")

    def test_frontoffice_detail_est_une_page_complete(self):
        response = self.client.get(reverse("ruches_front:detail", args=[self.ruche.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Détail de la colonie")
        self.assertContains(response, "R-001")
        self.assertContains(response, "45000")
        self.assertContains(response, "rf-photo-dadant")
        self.assertContains(response, "data-hive-3d")

    def test_export_pdf_par_type_et_par_etat(self):
        for regroupement in ("type", "etat"):
            response = self.client.get(
                reverse("ruches:exporter_pdf"),
                {"regroupement": regroupement},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertIn(f"ruches_par_{regroupement}", response["Content-Disposition"])
            self.assertTrue(response.content.startswith(b"%PDF"))
            lecteur = PdfReader(BytesIO(response.content))
            texte = "\n".join(page.extract_text() or "" for page in lecteur.pages)
            self.assertIn("BeeFlow", texte)
            self.assertIn("R-001", texte)


class RucheFormTests(TestCase):
    def test_refuse_une_date_future(self):
        form = RucheForm(
            data={
                "code_ruche": "R-100",
                "type_ruche": "Dadant",
                "race_abeilles": "Buckfast",
                "date_installation": (date.today() + timedelta(days=1)).isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 20_000,
                "etat_predit": EtatPredit.BON,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("date_installation", form.errors)

    def test_refuse_un_code_invalide(self):
        form = RucheForm(
            data={
                "code_ruche": "Ruche 100",
                "type_ruche": "Dadant",
                "race_abeilles": "Buckfast",
                "date_installation": date.today().isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 20_000,
                "etat_predit": EtatPredit.BON,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("code_ruche", form.errors)


@override_settings(ROOT_URLCONF="BeeFlow.urls")
class RucheFrontCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.apiculteur = get_user_model().objects.create_user(
            username="api-front",
            email="api-front@beeflow.test",
            password="TestBeeFlow123!",
            sexe="femme",
            date_naissance=date(1990, 1, 1),
            role="apiculteur",
            telephone="+21612345678",
        )

    def setUp(self):
        self.client.force_login(self.apiculteur)

    def test_catalogue_affiche_mon_espace_et_le_bouton_ajouter(self):
        response = self.client.get(reverse("ruches_front:liste"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("espace"))
        self.assertContains(response, "Mon espace")
        self.assertContains(response, reverse("ruches_front:ajouter"))
        self.assertContains(response, "Ajouter une ruche")

    def test_formulaire_front_reprend_le_style_back_sans_choix_utilisateur(self):
        response = self.client.get(reverse("ruches_front:ajouter"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "css/ruche.css")
        self.assertContains(response, reverse("espace"))
        self.assertNotContains(response, 'name="user"', html=False)

    def test_ajout_front_apparait_dans_le_crud_back(self):
        response = self.client.post(
            reverse("ruches_front:ajouter"),
            {
                "code_ruche": "FRONT-001",
                "type_ruche": "Dadant",
                "race_abeilles": "Buckfast",
                "date_installation": date.today().isoformat(),
                "presence_reine": "on",
                "nombre_abeilles": 32_000,
                "etat_predit": EtatPredit.BON,
                "idZone": "",
                "user": 999999,
            },
        )
        self.assertRedirects(response, reverse("ruches_front:liste"))

        ruche = Ruche.objects.get(code_ruche="FRONT-001")
        self.assertEqual(ruche.user, self.apiculteur)

        tableau_crud = self.client.get(reverse("ruches:liste"))
        self.assertEqual(tableau_crud.status_code, 200)
        self.assertContains(tableau_crud, "FRONT-001")
