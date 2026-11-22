"""Logique de recherche / filtre / tri partagée par le front office et le back office."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.paginator import Paginator
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone

from .forms import RechercheProduitForm
from .models import EtatProduit, Produit

PAR_PAGE = 9
TRIS = {
    "identifiant": "pk",
    "prix": "prix",
    "quantite": "quantite",
}
# Au-delà, l'entier ne peut pas être un identifiant (évite un dépassement SQLite)
MAX_CHIFFRES_ID = 18


def filtrer_produits(params):
    """Retourne (queryset, tri, sens) à partir des paramètres GET."""
    produits = Produit.objects.all()

    # Recherche exacte par identifiant ou par code-barres uniquement
    recherche = params.get("q", "").strip()
    if recherche:
        if recherche.isdigit():
            filtre = Q(code_barre=recherche)
            if len(recherche) <= MAX_CHIFFRES_ID:
                filtre |= Q(pk=int(recherche))
            produits = produits.filter(filtre)
        else:
            produits = produits.filter(code_barre=recherche)

    categorie = params.get("categorie", "").strip()
    origine = params.get("origine", "").strip()
    etat = params.get("etat", "").strip()

    categories_valides = {value for value, _ in Produit._meta.get_field("categorie_produit").choices}
    etats_valides = {value for value, _ in EtatProduit.choices}
    if categorie in categories_valides:
        produits = produits.filter(categorie_produit=categorie)
    if origine:
        produits = produits.filter(origine_florale__iexact=origine)
    if etat in etats_valides:
        produits = produits.filter(etat=etat)

    tri = params.get("tri", "identifiant")
    if tri not in TRIS:
        tri = "identifiant"
    sens = params.get("sens", "desc")
    if sens not in ("asc", "desc"):
        sens = "desc"
    champ_tri = TRIS[tri]
    if sens == "desc":
        champ_tri = "-" + champ_tri
    return produits.order_by(champ_tri, "-pk"), tri, sens


def compteurs_produits():
    """Les 4 KPI du front office, calculés sur les données réelles (hors filtres)."""
    return Produit.objects.aggregate(
        total=Count("pk"),
        disponibles=Count("pk", filter=Q(etat=EtatProduit.DISPONIBLE)),
        archives=Count("pk", filter=Q(etat=EtatProduit.ARCHIVE)),
        ruptures=Count("pk", filter=Q(etat=EtatProduit.RUPTURE_STOCK)),
    )


def origines_disponibles():
    return (Produit.objects.exclude(origine_florale__exact="")
            .exclude(origine_florale__isnull=True)
            .values_list("origine_florale", flat=True).distinct().order_by("origine_florale"))


def contexte_liste(request):
    """Contexte commun des deux listes (front : cartes, back : tableau)."""
    produits, tri, sens = filtrer_produits(request.GET)
    page = Paginator(produits, PAR_PAGE).get_page(request.GET.get("page"))

    form = RechercheProduitForm(
        initial={
            "q": request.GET.get("q", "").strip(),
            "categorie": request.GET.get("categorie", ""),
            "origine": request.GET.get("origine", ""),
            "etat": request.GET.get("etat", ""),
            "tri": tri, "sens": sens,
        },
        origines=origines_disponibles(),
    )
    # Conserver les filtres dans les liens de pagination
    params = request.GET.copy()
    params.pop("page", None)

    return {
        "form": form,
        "page": page,
        "total_count": page.paginator.count,
        "nb_total": Produit.objects.count(),
        "kpis": compteurs_produits(),
        "params": params.urlencode(),
        "filtres_actifs": any(request.GET.get(k, "").strip() for k in ("q", "categorie", "origine", "etat")),
    }


def png_code_barre(code):
    """PNG du code EAN-13 (python-barcode attend 12 chiffres et calcule la clé).
    Lève ImportError si python-barcode / Pillow ne sont pas installés."""
    import barcode
    from barcode.writer import ImageWriter

    ean = barcode.get("ean13", code[:12], writer=ImageWriter())
    buffer = BytesIO()
    ean.write(buffer, options={
        "module_width": 0.22, "module_height": 20.0, "quiet_zone": 3.5,
        "font_size": 9, "text_distance": 4.5, "write_text": True,
        "background": "white", "foreground": "black",
    })
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Statistiques (onglet « Statistiques » du back office) : données réelles uniquement
# ---------------------------------------------------------------------------
def _pct(partie, total):
    return round(partie * 100 / total) if total else 0


def _mois_suivant(d):
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def statistiques_produits():
    """Dictionnaire JSON-compatible : alimente la page Statistiques et son rafraîchissement automatique."""
    c = compteurs_produits()
    total = c["total"]
    taux_dispo = _pct(c["disponibles"], total)

    # Répartition par état
    etats = list(EtatProduit)
    par_etat = {"labels": [e.label for e in etats], "keys": [e.value for e in etats],
                "data": [c[{"disponible": "disponibles", "rupture_stock": "ruptures", "archive": "archives"}[e.value]] for e in etats]}

    # Répartition par catégorie, empilée par état
    categories = list(Produit._meta.get_field("categorie_produit").choices)
    lignes = {(l["categorie_produit"], l["etat"]): l["nb"]
              for l in Produit.objects.order_by().values("categorie_produit", "etat").annotate(nb=Count("pk"))}
    par_categorie = {
        "labels": [lib for _, lib in categories],
        "series": [{"key": e.value, "label": e.label, "data": [lignes.get((cle, e.value), 0) for cle, _ in categories]} for e in etats],
    }
    nb_par_cat = [sum(serie["data"][i] for serie in par_categorie["series"]) for i in range(len(categories))]

    # Valeur du stock disponible (quantité × prix unitaire, en TND) et prix moyen
    valeur = Produit.objects.filter(etat=EtatProduit.DISPONIBLE).aggregate(
        v=Sum(ExpressionWrapper(F("quantite") * F("prix"), output_field=DecimalField(max_digits=16, decimal_places=2))))["v"] or Decimal("0")
    prix_moyen = Produit.objects.aggregate(m=Avg("prix"))["m"] or Decimal("0")

    # Évolution sur 12 mois (produits ajoutés / cumul)
    dates = [timezone.localtime(d).date() for d in Produit.objects.values_list("created_at", flat=True)]
    auj = date.today()
    debut = auj.replace(day=1)
    for _ in range(11):
        debut = (debut - timedelta(days=1)).replace(day=1)
    avant = sum(1 for d in dates if d < debut)
    labels, ajoutes, cumul = [], [], []
    mois, courant = debut, avant
    for _ in range(12):
        nb = sum(1 for d in dates if (d.year, d.month) == (mois.year, mois.month))
        courant += nb
        labels.append(mois.strftime("%m/%Y"))
        ajoutes.append(nb)
        cumul.append(courant)
        mois = _mois_suivant(mois)
    evolution = {"labels": labels, "ajoutes": ajoutes, "cumul": cumul}
    ce_mois, mois_prec = ajoutes[-1], ajoutes[-2]

    return {
        "total": total, "compteurs": c, "taux_disponibilite": taux_dispo,
        "par_etat": par_etat, "par_categorie": par_categorie, "evolution": evolution,
        "ce_mois": ce_mois, "mois_prec": mois_prec, "nb_categories": len(categories),
        "taux_rupture": _pct(c["ruptures"], total), "taux_archive": _pct(c["archives"], total),
        "par_categorie_total": nb_par_cat,
        "valeur_stock": float(valeur), "prix_moyen": float(prix_moyen),
    }
