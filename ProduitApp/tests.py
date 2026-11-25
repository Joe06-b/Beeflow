import shutil
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from StocksApp.models import Stock
from .models import Produit

# PNG 1x1 valide, pour tester l'envoi de photo
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82")

DONNEES = {
    "categorie_produit": "miel", "origine_florale": "Lavande",
    "quantite": "1.50", "unite": "kg", "prix": "28.00",
    "etat": "disponible", "description_sensorielle": "Floral et doux",
}


class BaseTest(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            nom_stock="Stock test", type_stock="MIEL", emplacement="Entrepôt",
            capacite_max=Decimal("500"), seuil_alerte_min=Decimal("10"), seuil_alerte_max=Decimal("400"),
        )
        DONNEES["stock"] = str(self.stock.pk)
        self.p1 = Produit.objects.create(categorie_produit="miel", origine_florale="Thym", quantite="2.00", unite="kg", prix="35.00", etat="disponible")
        self.p2 = Produit.objects.create(categorie_produit="pollen", origine_florale="Fleurs sauvages", quantite="0.00", unite="g", prix="12.00", etat="rupture_stock")


class ModeleTests(BaseTest):
    def test_code_barre_ean13_genere_et_valide(self):
        code = self.p1.code_barre
        self.assertEqual(len(code), 13)
        self.assertTrue(code.isdigit())
        total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(code[:12]))
        self.assertEqual(int(code[12]), (10 - total % 10) % 10)
        self.assertNotEqual(self.p1.code_barre, self.p2.code_barre)

    def test_code_barre_conserve_a_la_modification(self):
        code = self.p1.code_barre
        self.p1.prix = Decimal("40")
        self.p1.save()
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.code_barre, code)

    def test_disponible_exige_quantite_positive(self):
        with self.assertRaises(ValidationError):
            Produit.objects.create(categorie_produit="miel", quantite="0", prix="10", etat="disponible")

    def test_rupture_exige_quantite_nulle(self):
        with self.assertRaises(ValidationError):
            Produit.objects.create(categorie_produit="miel", quantite="3", prix="10", etat="rupture_stock")

    def test_valeurs_negatives_refusees(self):
        with self.assertRaises(ValidationError):
            Produit.objects.create(categorie_produit="miel", quantite="-1", prix="10", etat="archive")
        with self.assertRaises(ValidationError):
            Produit.objects.create(categorie_produit="miel", quantite="1", prix="-10", etat="archive")


class RechercheFiltresTests(BaseTest):
    def test_frontoffice_search_by_primary_key(self):
        response = self.client.get(reverse("produits_front:liste"), {"q": str(self.p1.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Produit #{self.p1.pk}")
        self.assertNotContains(response, f"Produit #{self.p2.pk}")

    def test_frontoffice_search_by_barcode(self):
        response = self.client.get(reverse("produits_front:liste"), {"q": self.p2.code_barre})
        self.assertContains(response, f"Produit #{self.p2.pk}")
        self.assertNotContains(response, f"Produit #{self.p1.pk}")

    def test_recherche_texte_libre_exacte_seulement(self):
        response = self.client.get(reverse("produits_front:liste"), {"q": "Thym"})
        self.assertEqual(response.context["total_count"], 0)

    def test_recherche_nombre_enorme_ne_plante_pas(self):
        response = self.client.get(reverse("produits_front:liste"), {"q": "9" * 40})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 0)

    def test_filters_can_be_combined(self):
        response = self.client.get(reverse("produits_front:liste"), {"categorie": "miel", "origine": "thym", "etat": "disponible"})
        self.assertContains(response, f"Produit #{self.p1.pk}")
        self.assertNotContains(response, f"Produit #{self.p2.pk}")

    def test_filtre_invalide_ignore(self):
        response = self.client.get(reverse("produits_front:liste"), {"categorie": "nimporte", "etat": "xxx"})
        self.assertEqual(response.context["total_count"], 2)

    def test_tri_quantite(self):
        response = self.client.get(reverse("produits_front:liste"), {"tri": "quantite", "sens": "asc"})
        self.assertEqual([p.pk for p in response.context["page"]], [self.p2.pk, self.p1.pk])
        response = self.client.get(reverse("produits_front:liste"), {"tri": "identifiant", "sens": "desc"})
        self.assertEqual([p.pk for p in response.context["page"]], [self.p2.pk, self.p1.pk])

    def test_backoffice_list_accepts_filters(self):
        response = self.client.get(reverse("produits:liste"), {"categorie": "pollen", "etat": "rupture_stock", "tri": "quantite"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#{self.p2.pk}")
        self.assertNotContains(response, f"#{self.p1.pk}<")

    def test_pagination_conserve_les_filtres(self):
        for i in range(12):
            Produit.objects.create(categorie_produit="cire", quantite="1", prix="5", etat="disponible")
        response = self.client.get(reverse("produits:liste"), {"categorie": "cire", "page": 2})
        self.assertEqual(response.context["page"].number, 2)
        self.assertEqual(len(response.context["page"]), 3)
        self.assertContains(response, "categorie=cire&page=1")


class CodeBarreTests(BaseTest):
    def test_barcode_image_endpoint_returns_png(self):
        for nom in ("produits:code_barre_image", "produits_front:code_barre_image"):
            response = self.client.get(reverse(nom, args=[self.p1.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertTrue(response.content.startswith(b"\x89PNG"))

    def test_barcode_produit_inconnu(self):
        self.assertEqual(self.client.get(reverse("produits:code_barre_image", args=[9999])).status_code, 404)


class FrontofficeCrudTests(BaseTest):
    def test_pages_accessibles(self):
        for nom, args in [("liste", []), ("ajouter", []), ("detail", [self.p1.pk]), ("modifier", [self.p1.pk]), ("supprimer", [self.p1.pk])]:
            response = self.client.get(reverse(f"produits_front:{nom}", args=args))
            self.assertEqual(response.status_code, 200, nom)

    def test_create_product(self):
        response = self.client.post(reverse("produits_front:ajouter"), DONNEES)
        produit = Produit.objects.get(origine_florale="Lavande")
        self.assertRedirects(response, reverse("produits_front:detail", args=[produit.pk]))
        self.assertTrue(produit.code_barre)

    def test_create_avec_photo(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post(reverse("produits_front:ajouter"), {**DONNEES, "photo_produit": SimpleUploadedFile("p.png", PNG, "image/png")})
            self.assertEqual(response.status_code, 302)
            produit = Produit.objects.get(origine_florale="Lavande")
            self.assertTrue(produit.photo_produit.name.startswith("produits/"))
            self.assertEqual(self.client.get(reverse("produits_front:detail", args=[produit.pk])).status_code, 200)
            self.assertEqual(self.client.get(reverse("produits:liste")).status_code, 200)

    def test_create_invalide_affiche_les_erreurs(self):
        response = self.client.post(reverse("produits_front:ajouter"), {**DONNEES, "quantite": "0"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quantité supérieure à 0")
        self.assertFalse(Produit.objects.filter(origine_florale="Lavande").exists())

    def test_create_champs_obligatoires(self):
        response = self.client.post(reverse("produits_front:ajouter"), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_update_product(self):
        response = self.client.post(reverse("produits_front:modifier", args=[self.p1.pk]), {**DONNEES, "origine_florale": "Romarin", "quantite": "3.00", "prix": "37.00"})
        self.assertRedirects(response, reverse("produits_front:detail", args=[self.p1.pk]))
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.origine_florale, "Romarin")
        self.assertEqual(self.p1.prix, Decimal("37.00"))

    def test_delete_get_ne_supprime_pas(self):
        self.client.get(reverse("produits_front:supprimer", args=[self.p2.pk]))
        self.assertTrue(Produit.objects.filter(pk=self.p2.pk).exists())

    def test_delete_product_requires_post(self):
        response = self.client.post(reverse("produits_front:supprimer", args=[self.p2.pk]))
        self.assertRedirects(response, reverse("produits_front:liste"))
        self.assertFalse(Produit.objects.filter(pk=self.p2.pk).exists())

    def test_messages_de_confirmation(self):
        response = self.client.post(reverse("produits_front:ajouter"), DONNEES, follow=True)
        self.assertContains(response, "ajouté avec succès")

class StockAffectationTests(BaseTest):
    def test_stock_obligatoire_a_l_ajout(self):
        donnees = {k: v for k, v in DONNEES.items() if k != "stock"}
        response = self.client.post(reverse("produits_front:ajouter"), donnees)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Veuillez choisir le stock d")

    def test_stock_enregistre_avec_le_produit(self):
        response = self.client.post(reverse("produits_front:ajouter"), DONNEES)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Produit.objects.latest("pk").stock, self.stock)

    def test_liste_deroulante_affiche_l_id_du_stock(self):
        response = self.client.get(reverse("produits_front:ajouter"))
        self.assertContains(response, f"#{self.stock.pk} – Stock test")
class BackofficeCrudTests(BaseTest):
    def test_pages_accessibles(self):
        for nom, args in [("liste", []), ("ajouter", []), ("detail", [self.p1.pk]), ("modifier", [self.p1.pk]), ("supprimer", [self.p1.pk])]:
            response = self.client.get(reverse(f"produits:{nom}", args=args))
            self.assertEqual(response.status_code, 200, nom)
            self.assertEqual(response.context["active_page"], "production")

    def test_backoffice_create_product(self):
        response = self.client.post(reverse("produits:ajouter"), {**DONNEES, "origine_florale": "Acacia"})
        self.assertRedirects(response, reverse("produits:liste"))
        self.assertTrue(Produit.objects.filter(origine_florale="Acacia").exists())

    def test_backoffice_create_invalide(self):
        response = self.client.post(reverse("produits:ajouter"), {**DONNEES, "etat": "rupture_stock"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quantité égale à 0")

    def test_backoffice_update_product(self):
        response = self.client.post(reverse("produits:modifier", args=[self.p1.pk]), {**DONNEES, "origine_florale": "Fleurs sauvages", "quantite": "4.00", "prix": "39.00"})
        self.assertRedirects(response, reverse("produits:liste"))
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.origine_florale, "Fleurs sauvages")

    def test_backoffice_delete(self):
        self.assertEqual(self.client.get(reverse("produits:supprimer", args=[self.p1.pk])).status_code, 200)
        self.assertTrue(Produit.objects.filter(pk=self.p1.pk).exists())
        response = self.client.post(reverse("produits:supprimer", args=[self.p1.pk]))
        self.assertRedirects(response, reverse("produits:liste"))
        self.assertFalse(Produit.objects.filter(pk=self.p1.pk).exists())

    def test_produit_inconnu_404(self):
        for nom in ("detail", "modifier", "supprimer"):
            self.assertEqual(self.client.get(reverse(f"produits:{nom}", args=[9999])).status_code, 404)


class IntegrationTests(TestCase):
    def test_navigation_vers_le_module(self):
        self.assertContains(self.client.get(reverse("dashboard")), reverse("produits:liste"))
        self.assertContains(self.client.get(reverse("espace")), reverse("produits_front:liste"))

    def test_autres_modules_intacts(self):
        for nom in ("accueil", "espace", "dashboard", "suivi_sanitaire:liste", "suivi_sanitaire_bo:liste", "suivi_sanitaire_bo:statistiques"):
            self.assertEqual(self.client.get(reverse(nom)).status_code, 200, nom)
