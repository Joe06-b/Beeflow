from io import BytesIO
import socket
from urllib.parse import urljoin

from django.conf import settings
from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import RucheForm
from .models import ActionHistorique, EtatPredit, HistoriqueRuche, RaceAbeilles, Ruche, TypeRuche
from .pdf_export import generer_pdf_ruches


def adresse_ipv4_locale():
    """Retourne l'adresse de l'interface réseau utilisée pour sortir du PC."""
    connexion = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connexion.connect(("8.8.8.8", 80))
        return connexion.getsockname()[0]
    except OSError:
        return None
    finally:
        connexion.close()


def url_publique_ruche(request, ruche):
    """Construit l'URL encodée dans le QR de la ruche."""
    chemin = reverse("ruches_front:scan_detail_token", args=[ruche.qr_token])
    base_publique = getattr(settings, "BEEFLOW_QR_BASE_URL", "").strip()
    if base_publique:
        return urljoin(f"{base_publique.rstrip('/')}/", chemin.lstrip("/"))

    hote_demande = request.get_host()
    nom_hote = hote_demande.split(":", 1)[0].strip("[]").lower()
    if nom_hote in {"localhost", "127.0.0.1", "::1", "testserver"}:
        ip_locale = adresse_ipv4_locale()
        if ip_locale:
            port = (
                hote_demande.rsplit(":", 1)[1]
                if hote_demande.count(":") == 1
                else request.get_port()
            )
            suffixe_port = "" if port in {"80", "443"} else f":{port}"
            return f"{request.scheme}://{ip_locale}{suffixe_port}{chemin}"
    return request.build_absolute_uri(chemin)


def auteur_historique(request):
    if request.user.is_authenticated:
        return request.user.get_full_name() or request.user.get_username()
    return "Système"


class GestionRuchesContextMixin:
    """Contexte commun à toutes les pages du CRUD back-office."""

    page_title = "Gestion des ruches"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["active_page"] = "ruches"
        return context


class RechercheTriRucheMixin:
    tris_autorises = {
        "code": "code_ruche",
        "code_desc": "-code_ruche",
        "date": "date_installation",
        "date_desc": "-date_installation",
        "population": "nombre_abeilles",
        "population_desc": "-nombre_abeilles",
    }

    def get_filtres_actifs(self):
        """Nettoie les paramètres GET utilisés par les listes front et back."""
        type_demande = self.request.GET.get("type", "").strip()
        etat_demande = self.request.GET.get("etat", "").strip()
        tri_demande = self.request.GET.get("tri", "code").strip()

        return {
            "q": self.request.GET.get("q", "").strip(),
            "type": type_demande if type_demande in TypeRuche.values else "",
            "etat": etat_demande if etat_demande in EtatPredit.values else "",
            "tri": tri_demande if tri_demande in self.tris_autorises else "code",
        }

    def get_queryset(self):
        queryset = Ruche.objects.all()
        filtres = self.get_filtres_actifs()

        if filtres["q"]:
            queryset = queryset.filter(
                Q(code_ruche__icontains=filtres["q"])
                | Q(type_ruche__icontains=filtres["q"])
                | Q(race_abeilles__icontains=filtres["q"])
            )
        if filtres["type"]:
            queryset = queryset.filter(type_ruche__iexact=filtres["type"])
        if filtres["etat"]:
            queryset = queryset.filter(etat_predit=filtres["etat"])

        ordre = self.tris_autorises[filtres["tri"]]
        champs_tri = [ordre]
        if ordre.lstrip("-") != "code_ruche":
            champs_tri.append("code_ruche")
        return queryset.order_by(*champs_tri)


class RucheListView(GestionRuchesContextMixin, RechercheTriRucheMixin, ListView):
    model = Ruche
    template_name = "ruches/liste.html"
    context_object_name = "ruches"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ruches_filtrees = self.get_queryset()
        params = self.request.GET.copy()
        params.pop("page", None)

        context.update(
            {
                "nb_resultats": ruches_filtrees.count(),
                "nb_avec_reine": ruches_filtrees.filter(presence_reine=True).count(),
                "nb_a_surveiller": ruches_filtrees.exclude(etat_predit=EtatPredit.BON).count(),
                "population_totale": ruches_filtrees.aggregate(total=Sum("nombre_abeilles"))["total"] or 0,
                "types_ruches": TypeRuche.choices,
                "etats": EtatPredit.choices,
                "filtres": self.get_filtres_actifs(),
                "params": params.urlencode(),
            }
        )
        return context


class RucheStatistiquesView(GestionRuchesContextMixin, TemplateView):
    template_name = "ruches/statistiques.html"
    page_title = "Statistiques des ruches"

    @staticmethod
    def _repartition(queryset, champ, libelles):
        compteurs = {
            ligne[champ]: ligne["nb"]
            for ligne in queryset.values(champ).annotate(nb=Count("id_ruche"))
        }
        valeurs = list(libelles.keys())
        valeurs.extend(valeur for valeur in compteurs if valeur not in libelles)
        return [
            {"valeur": valeur, "label": libelles.get(valeur, valeur), "nb": compteurs.get(valeur, 0)}
            for valeur in valeurs
            if compteurs.get(valeur, 0)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Ruche.objects.all()
        total = queryset.count()
        population = queryset.aggregate(total=Sum("nombre_abeilles"), moyenne=Avg("nombre_abeilles"))
        par_etat = self._repartition(queryset, "etat_predit", dict(EtatPredit.choices))
        par_type = self._repartition(queryset, "type_ruche", dict(TypeRuche.choices))
        par_race = self._repartition(queryset, "race_abeilles", dict(RaceAbeilles.choices))

        nb_bon = queryset.filter(etat_predit=EtatPredit.BON).count()
        nb_surveillance = queryset.filter(etat_predit=EtatPredit.A_SURVEILLER).count()
        nb_risque = queryset.filter(etat_predit=EtatPredit.RISQUE_ELEVE).count()
        nb_avec_reine = queryset.filter(presence_reine=True).count()

        stats = {
            "total": total,
            "population_totale": population["total"] or 0,
            "population_moyenne": round(population["moyenne"] or 0),
            "nb_avec_reine": nb_avec_reine,
            "taux_avec_reine": round(nb_avec_reine * 100 / total) if total else 0,
            "nb_bon": nb_bon,
            "nb_surveillance": nb_surveillance,
            "nb_risque": nb_risque,
            "par_etat": par_etat,
            "par_type": sorted(par_type, key=lambda element: (-element["nb"], element["label"])),
            "par_race": sorted(par_race, key=lambda element: (-element["nb"], element["label"])),
            "dernieres_ruches": queryset.order_by("-date_installation", "code_ruche")[:5],
        }
        graphiques = {
            "etat": {
                "labels": [element["label"] for element in par_etat],
                "data": [element["nb"] for element in par_etat],
            },
            "type": {
                "labels": [element["label"] for element in stats["par_type"]],
                "data": [element["nb"] for element in stats["par_type"]],
            },
            "race": {
                "labels": [element["label"] for element in stats["par_race"]],
                "data": [element["nb"] for element in stats["par_race"]],
            },
        }
        context.update({"stats": stats, "graphiques": graphiques})
        return context


class RucheHistoriqueView(GestionRuchesContextMixin, ListView):
    model = HistoriqueRuche
    template_name = "ruches/historique.html"
    context_object_name = "historiques"
    paginate_by = 20
    page_title = "Historique des ruches"

    def get_queryset(self):
        queryset = HistoriqueRuche.objects.select_related("ruche")
        recherche = self.request.GET.get("q", "").strip()
        action = self.request.GET.get("action", "").strip()
        if recherche:
            queryset = queryset.filter(
                Q(code_ruche__icontains=recherche) | Q(auteur__icontains=recherche)
            )
        if action in ActionHistorique.values:
            queryset = queryset.filter(action=action)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        context.update(
            {
                "actions_historique": ActionHistorique.choices,
                "nb_resultats": self.get_queryset().count(),
                "params": params.urlencode(),
            }
        )
        return context


class HistoriqueRucheDeleteView(GestionRuchesContextMixin, DeleteView):
    model = HistoriqueRuche
    template_name = "ruches/confirm_delete_historique.html"
    context_object_name = "entree"
    success_url = reverse_lazy("ruches:historique")
    page_title = "Supprimer une entrée d'historique"

    def form_valid(self, form):
        code_ruche = self.object.code_ruche
        response = super().form_valid(form)
        messages.success(self.request, f"L'entrée d'historique de {code_ruche} a été supprimée.")
        return response


class RucheExportPdfView(View):
    def get(self, request, *args, **kwargs):
        regroupement = "etat" if request.GET.get("regroupement") == "etat" else "type"
        contenu = generer_pdf_ruches(Ruche.objects.order_by("code_ruche"), regroupement)
        date_export = timezone.localdate().strftime("%Y%m%d")
        response = HttpResponse(contenu, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="ruches_par_{regroupement}_{date_export}.pdf"'
        )
        return response


class RucheFrontListView(RechercheTriRucheMixin, ListView):
    model = Ruche
    template_name = "ruches/catalogue.html"
    context_object_name = "ruches"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.object_list
        context.update(
            {
                "nb_resultats": queryset.count(),
                "nb_bon": queryset.filter(etat_predit=EtatPredit.BON).count(),
                "nb_surveillance": queryset.filter(etat_predit=EtatPredit.A_SURVEILLER).count(),
                "population_totale": queryset.aggregate(total=Sum("nombre_abeilles"))["total"] or 0,
                "nb_risque": queryset.filter(etat_predit=EtatPredit.RISQUE_ELEVE).count(),
                "types_ruches": TypeRuche.choices,
                "etats": EtatPredit.choices,
                "filtres": self.get_filtres_actifs(),
            }
        )
        return context


class RucheFrontDetailView(DetailView):
    model = Ruche
    template_name = "ruches/catalogue_detail.html"
    context_object_name = "ruche"



class RucheDetailView(GestionRuchesContextMixin, DetailView):
    model = Ruche
    template_name = "ruches/detail.html"
    context_object_name = "ruche"


class RucheCreateView(GestionRuchesContextMixin, CreateView):
    model = Ruche
    form_class = RucheForm
    template_name = "ruches/form.html"
    success_url = reverse_lazy("ruches:liste")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"mode": "ajout", "form_title": "Ajouter une ruche"})
        return context

    def form_valid(self, form):
        messages.success(self.request, f"La ruche {form.instance.code_ruche} a été ajoutée.")
        response = super().form_valid(form)
        HistoriqueRuche.enregistrer(
            self.object,
            ActionHistorique.AJOUT,
            apres=self.object.valeurs_historiques(),
            auteur=auteur_historique(self.request),
        )
        return response


class RucheUpdateView(GestionRuchesContextMixin, UpdateView):
    model = Ruche
    form_class = RucheForm
    template_name = "ruches/form.html"
    context_object_name = "ruche"
    success_url = reverse_lazy("ruches:liste")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"mode": "modification", "form_title": "Modifier la ruche"})
        return context

    def form_valid(self, form):
        avant = Ruche.objects.get(pk=self.object.pk).valeurs_historiques()
        messages.success(self.request, f"La ruche {form.instance.code_ruche} a été modifiée.")
        response = super().form_valid(form)
        HistoriqueRuche.enregistrer(
            self.object,
            ActionHistorique.MODIFICATION,
            avant=avant,
            apres=self.object.valeurs_historiques(),
            auteur=auteur_historique(self.request),
        )
        return response


class RucheDeleteView(GestionRuchesContextMixin, DeleteView):
    model = Ruche
    template_name = "ruches/confirm_delete.html"
    context_object_name = "ruche"
    success_url = reverse_lazy("ruches:liste")

    def form_valid(self, form):
        code_ruche = self.object.code_ruche
        HistoriqueRuche.enregistrer(
            self.object,
            ActionHistorique.SUPPRESSION,
            avant=self.object.valeurs_historiques(),
            auteur=auteur_historique(self.request),
        )
        response = super().form_valid(form)
        messages.success(self.request, f"La ruche {code_ruche} a été supprimée.")
        return response
