"""
ATLAS DES MALADIES DE L'ABEILLE — données d'affichage uniquement.
Aucun modèle, aucune migration : ces fiches sont écrites ici, dans le code.

Ce sont des informations générales sur les maladies courantes de l'abeille.
Elles ne remplacent pas l'avis d'un vétérinaire ou des services vétérinaires officiels,
et les règles de déclaration dépendent du pays.

Chaque fiche :
    slug, nom, nom_scientifique, categorie, gravite (1 à 5), a_signaler (bool),
    resume, symptomes, conduite, prevention, mots_cles (pour reconnaître la maladie
    dans le champ libre « maladie_detectee » des suivis)
"""
import unicodedata

CATEGORIES = {
    "parasite": "Parasite",
    "bacterie": "Bactérie",
    "champignon": "Champignon",
    "virus": "Virus",
    "predateur": "Prédateur",
}

MALADIES = [
    {
        "slug": "varroase",
        "nom": "Varroase",
        "nom_scientifique": "Varroa destructor",
        "categorie": "parasite",
        "gravite": 5,
        "a_signaler": False,
        "resume": "Un acarien qui se nourrit des abeilles et du couvain, et transmet des virus. "
                  "C'est la première cause d'affaiblissement des colonies.",
        "symptomes": [
            "Petits acariens brun-rouge sur les abeilles ou dans le couvain",
            "Abeilles aux ailes déformées, incapables de voler",
            "Couvain irrégulier, en mosaïque",
            "Colonie qui s'affaiblit à la fin de l'été",
        ],
        "conduite": [
            "Compter la chute naturelle d'acariens sur un lange graissé",
            "Traiter avec un produit autorisé (acide oxalique, acide formique, thymol…)",
            "Traiter toutes les ruches du rucher en même temps",
        ],
        "prevention": [
            "Surveiller le niveau d'infestation chaque mois",
            "Retirer le couvain de mâles, très recherché par l'acarien",
            "Prévoir un traitement après la dernière récolte",
        ],
        "mots_cles": ["varroa", "varroase", "varroose", "varroatose"],
        "recherche": "varroa",
    },
    {
        "slug": "loque-americaine",
        "nom": "Loque américaine",
        "nom_scientifique": "Paenibacillus larvae",
        "categorie": "bacterie",
        "gravite": 5,
        "a_signaler": True,
        "resume": "Une bactérie très contagieuse qui tue les larves après l'operculation. "
                  "Ses spores survivent des dizaines d'années dans le matériel.",
        "symptomes": [
            "Opercules affaissés, gras et parfois percés",
            "Larves brunes et filantes (test de l'allumette : un fil se forme)",
            "Couvain en mosaïque et odeur désagréable",
            "Écailles sèches collées au fond des cellules",
        ],
        "conduite": [
            "Ne déplacer aucun cadre ni aucune ruche",
            "Prévenir les services vétérinaires : c'est une maladie à signaler",
            "Suivre les mesures imposées (destruction ou transvasement)",
        ],
        "prevention": [
            "Ne jamais nourrir avec du miel d'origine inconnue",
            "Renouveler régulièrement les cadres",
            "Désinfecter le matériel à la flamme",
        ],
        "mots_cles": ["loque americaine", "paenibacillus", "loque am"],
    },
    {
        "slug": "loque-europeenne",
        "nom": "Loque européenne",
        "nom_scientifique": "Melissococcus plutonius",
        "categorie": "bacterie",
        "gravite": 3,
        "a_signaler": True,
        "resume": "Une bactérie qui touche les jeunes larves avant l'operculation, "
                  "souvent quand la colonie manque de nourriture ou de force.",
        "symptomes": [
            "Larves jaunâtres puis brunes, tordues dans les cellules ouvertes",
            "Odeur aigre dans la ruche",
            "Couvain irrégulier",
        ],
        "conduite": [
            "Signaler la maladie aux services vétérinaires",
            "Renforcer la colonie et renouveler les cadres atteints",
            "Envisager le remplacement de la reine",
        ],
        "prevention": [
            "Garder des colonies fortes et bien nourries",
            "Éviter les échanges de cadres entre ruches",
        ],
        "mots_cles": ["loque europeenne", "melissococcus", "loque eu"],
    },
    {
        "slug": "nosemose",
        "nom": "Nosémose",
        "nom_scientifique": "Nosema apis, Nosema ceranae",
        "categorie": "champignon",
        "gravite": 3,
        "a_signaler": False,
        "resume": "Des micro-champignons qui envahissent l'intestin des abeilles adultes "
                  "et raccourcissent leur vie.",
        "symptomes": [
            "Traces de diarrhée sur la planche d'envol et les cadres",
            "Abeilles traînantes devant la ruche",
            "Dépopulation au printemps, parfois sans autre signe",
        ],
        "conduite": [
            "Confirmer par une analyse au microscope en laboratoire",
            "Remplacer les cadres souillés",
            "Regrouper ou renforcer les colonies faibles",
        ],
        "prevention": [
            "Hiverner les ruches au sec, à l'abri de l'humidité",
            "Nourrir avec une nourriture de qualité",
            "Renouveler les cires régulièrement",
        ],
        "mots_cles": ["nosema", "nosemose", "nosemiase"],
    },
    {
        "slug": "couvain-platre",
        "nom": "Couvain plâtré",
        "nom_scientifique": "Ascosphaera apis",
        "categorie": "champignon",
        "gravite": 2,
        "a_signaler": False,
        "resume": "Un champignon qui transforme les larves en petites momies dures, "
                  "favorisé par l'humidité et le froid.",
        "symptomes": [
            "Larves momifiées blanches ou grises, dures comme de la craie",
            "Momies au fond de la ruche ou devant l'entrée",
            "Couvain clairsemé",
        ],
        "conduite": [
            "Retirer les cadres très atteints",
            "Améliorer l'aération de la ruche",
            "Remplacer la reine si le problème revient",
        ],
        "prevention": [
            "Installer les ruches dans un endroit sec et ensoleillé",
            "Garder des colonies fortes",
        ],
        "mots_cles": ["couvain platre", "ascospherose", "ascosphaera", "platre"],
    },
    {
        "slug": "ailes-deformees",
        "nom": "Virus des ailes déformées",
        "nom_scientifique": "DWV (Deformed Wing Virus)",
        "categorie": "virus",
        "gravite": 4,
        "a_signaler": False,
        "resume": "Un virus transmis surtout par le varroa. Les abeilles naissent "
                  "avec des ailes froissées et meurent vite.",
        "symptomes": [
            "Ailes froissées ou atrophiées",
            "Abdomen court et gonflé",
            "Abeilles qui marchent sans pouvoir voler",
        ],
        "conduite": [
            "Il n'existe pas de traitement contre le virus lui-même",
            "Lutter contre le varroa, qui le transmet",
        ],
        "prevention": [
            "Garder le varroa sous contrôle toute l'année",
        ],
        "mots_cles": ["ailes deformees", "dwv", "virus des ailes"],
    },
    {
        "slug": "frelon-asiatique",
        "nom": "Frelon asiatique",
        "nom_scientifique": "Vespa velutina",
        "categorie": "predateur",
        "gravite": 4,
        "a_signaler": False,
        "resume": "Un frelon qui chasse les abeilles en vol devant la ruche. "
                  "La colonie, stressée, arrête de butiner.",
        "symptomes": [
            "Frelons en vol stationnaire devant l'entrée",
            "Abeilles qui ne sortent presque plus",
            "Réserves qui baissent à la fin de l'été",
        ],
        "conduite": [
            "Réduire l'entrée avec une grille de protection",
            "Utiliser des pièges sélectifs",
            "Faire détruire les nids par un professionnel",
        ],
        "prevention": [
            "Piéger les reines fondatrices au printemps",
            "Signaler les nids repérés à la mairie",
        ],
        "mots_cles": ["frelon", "vespa", "velutina"],
        "recherche": "frelon",
    },
    {
        "slug": "petit-coleoptere",
        "nom": "Petit coléoptère des ruches",
        "nom_scientifique": "Aethina tumida",
        "categorie": "parasite",
        "gravite": 4,
        "a_signaler": True,
        "resume": "Un petit scarabée dont les larves creusent les rayons. "
                  "Le miel fermente et coule hors des cadres.",
        "symptomes": [
            "Petits coléoptères brun-noir (5 à 7 mm) qui fuient la lumière",
            "Larves dans les rayons de miel et de couvain",
            "Miel fermenté qui coule, odeur d'orange pourrie",
        ],
        "conduite": [
            "Signaler immédiatement aux services vétérinaires",
            "Ne déplacer ni ruche ni matériel",
        ],
        "prevention": [
            "Inspecter régulièrement les ruches",
            "Garder des colonies fortes",
        ],
        "mots_cles": ["aethina", "coleoptere", "petit scarabee"],
    },
]


# ---------------------------------------------------------------------------
# ANATOMIE (page « Explorer en 3D ») — rôle de chaque partie, pour toutes les maladies
# ---------------------------------------------------------------------------
ANATOMIE = {
    "yeux": {"nom": "Yeux", "role": "Deux grands yeux composés, faits de milliers de petites facettes, et trois petits yeux simples (ocelles) sur le dessus de la tête. L'abeille voit l'ultraviolet, invisible pour nous.",
             "regarder": "Rien à surveiller en particulier : les yeux sont rarement touchés par les maladies."},
    "antennes": {"nom": "Antennes", "role": "Le nez et les doigts de l'abeille : elles sentent les odeurs, touchent, et servent à communiquer dans la ruche.",
                 "regarder": "Une abeille qui bouge peu ses antennes ou qui tremble peut être affaiblie."},
    "ailes": {"nom": "Ailes", "role": "Deux paires d'ailes accrochées l'une à l'autre en vol. Elles battent environ 230 fois par seconde : c'est le bourdonnement.",
              "regarder": "Des ailes froissées, trop courtes ou écartées sont un signe d'alerte."},
    "thorax": {"nom": "Thorax", "role": "Le centre moteur : il porte les ailes et les six pattes, et contient les muscles du vol.",
               "regarder": "Regardez s'il porte de petits points brun-rouge (acariens)."},
    "abdomen": {"nom": "Abdomen", "role": "Il contient le jabot (réserve de nectar), l'intestin, les glandes à cire et le dard.",
                "regarder": "Un abdomen gonflé, raccourci ou des acariens entre les anneaux sont des signes de maladie."},
    "pattes": {"nom": "Pattes", "role": "Trois paires de pattes. Les pattes arrière portent les corbeilles où l'abeille ramène le pollen.",
               "regarder": "Des pelotes de pollen montrent que la colonie butine normalement."},
    "dard": {"nom": "Dard", "role": "L'arme de défense des ouvrières. Il est barbelé : l'abeille meurt après avoir piqué un mammifère.",
             "regarder": "Rien à surveiller pour les maladies."},
    "intestin": {"nom": "Intestin", "role": "Il digère le nectar et le pollen. Il est caché à l'intérieur de l'abdomen.",
                 "regarder": "Il ne se voit pas à l'œil nu : une analyse au microscope est nécessaire."},
    "larve": {"nom": "Larve (couvain)", "role": "Le bébé abeille, couché en forme de C au fond de son alvéole. Il est nourri par les nourrices, puis l'alvéole est fermée (operculée) pour la transformation.",
              "regarder": "Une larve saine est blanc nacré, brillante et bien enroulée."},
}

# Pour chaque maladie : parties touchées (avec explication), effets visuels à appliquer au modèle 3D,
# et partie montrée en premier.
ANATOMIE_MALADIES = {
    "varroase": {
        "focus": "abdomen",
        "effets": ["acariens", "larve_acariens"],
        "atteintes": {
            "abdomen": "Les acariens se glissent entre les anneaux de l'abdomen et se nourrissent des réserves de l'abeille.",
            "thorax": "On voit souvent l'acarien, brun-rouge et ovale, accroché au thorax.",
            "larve": "Le varroa se reproduit dans les alvéoles de couvain : la larve est attaquée avant même de naître.",
            "ailes": "En transmettant des virus, le varroa provoque des ailes déformées chez les jeunes abeilles.",
        },
    },
    "loque-americaine": {
        "focus": "larve",
        "effets": ["larve_fondue", "opercule_perce"],
        "atteintes": {
            "larve": "La larve meurt après l'operculation, devient brune et fond en une masse filante.",
            "abdomen": "L'abeille adulte n'est pas malade, mais elle transporte les spores dans son jabot et contamine la ruche en nourrissant les larves.",
        },
    },
    "loque-europeenne": {
        "focus": "larve",
        "effets": ["larve_tordue"],
        "atteintes": {
            "larve": "La jeune larve meurt avant l'operculation : elle jaunit, brunit et se tord dans l'alvéole.",
            "abdomen": "Les nourrices transmettent la bactérie aux larves en les nourrissant.",
        },
    },
    "nosemose": {
        "focus": "intestin",
        "effets": ["intestin", "abdomen_gonfle"],
        "atteintes": {
            "intestin": "Les spores se multiplient dans les cellules de l'intestin : l'abeille digère mal et vit moins longtemps.",
            "abdomen": "L'abdomen peut paraître gonflé, et l'abeille souffre de diarrhée.",
            "ailes": "Les abeilles très atteintes volent mal et restent traînantes devant la ruche.",
        },
    },
    "couvain-platre": {
        "focus": "larve",
        "effets": ["larve_momie"],
        "atteintes": {
            "larve": "Le champignon envahit la larve, qui se transforme en momie blanche et dure comme de la craie.",
        },
    },
    "ailes-deformees": {
        "focus": "ailes",
        "effets": ["ailes_froissees", "abdomen_court"],
        "atteintes": {
            "ailes": "Les ailes naissent froissées et atrophiées : l'abeille ne pourra jamais voler.",
            "abdomen": "L'abdomen est souvent plus court et plus rond que la normale.",
        },
    },
    "frelon-asiatique": {
        "focus": "thorax",
        "effets": ["thorax_cible", "frelon"],
        "atteintes": {
            "thorax": "Le frelon capture la butineuse en vol et garde surtout le thorax, riche en muscles, pour nourrir ses larves.",
            "ailes": "Stressées, les abeilles ne sortent plus butiner : la colonie s'affaiblit.",
        },
    },
    "petit-coleoptere": {
        "focus": "larve",
        "effets": ["coleopteres"],
        "atteintes": {
            "larve": "Les larves du coléoptère dévorent le couvain, le pollen et le miel.",
        },
    },
}


def fiche_par_slug(slug):
    for m in MALADIES:
        if m["slug"] == slug:
            fiche = dict(m)
            fiche["categorie_label"] = CATEGORIES[m["categorie"]]
            fiche["gravite_range"] = range(1, 6)
            return fiche
    return None


def anatomie_pour(slug):
    """Données envoyées au script 3D (json_script)."""
    a = ANATOMIE_MALADIES[slug]
    return {
        "focus": a["focus"],
        "effets": a["effets"],
        "parties": {
            code: dict(info, atteinte=a["atteintes"].get(code, ""))
            for code, info in ANATOMIE.items()
        },
    }


def _normaliser(texte):
    """Minuscules, sans accents : « Loque Américaine » → « loque americaine »."""
    texte = unicodedata.normalize("NFD", (texte or "").lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn").strip()


def trouver_maladie(texte):
    """Retourne la fiche qui correspond au texte libre d'un suivi, ou None."""
    t = _normaliser(texte)
    if not t:
        return None
    for m in MALADIES:
        if any(mot in t for mot in m["mots_cles"]) or _normaliser(m["nom"]) in t:
            return m
    return None


def noms_maladies():
    return [m["nom"] for m in MALADIES]


def maladies_avec_detections(textes):
    """Ajoute à chaque fiche le nombre de suivis où elle a été détectée."""
    compte = {m["slug"]: 0 for m in MALADIES}
    for texte in textes:
        m = trouver_maladie(texte)
        if m:
            compte[m["slug"]] += 1
    fiches = []
    for m in MALADIES:
        fiche = dict(m)
        fiche["categorie_label"] = CATEGORIES[m["categorie"]]
        fiche["detections"] = compte[m["slug"]]
        fiche["gravite_range"] = range(1, 6)
        fiche["recherche"] = m.get("recherche", m["nom"])
        fiches.append(fiche)
    return fiches


# ---------------------------------------------------------------------------
# ÉVOLUTION DANS LA RUCHE (la « 4e dimension » : le temps)
# Paramètres PÉDAGOGIQUES d'une simulation simple, semaine par semaine :
#   depart    part de la colonie touchée au départ (0 à 1)
#   vitesse   vitesse de propagation chaque semaine
#   degats    perte d'abeilles par semaine quand toute la colonie est touchée
#   cible     ce que la maladie attaque d'abord : "couvain", "adultes" ou "butineuses"
#   traitement  semaine, efficacité (part de la maladie supprimée) et texte de l'action
#   etapes    ce qu'on voit sans rien faire ; apres_traitement : ce qu'on voit si on agit
# Ce ne sont pas des mesures réelles : l'ordre de grandeur et le déroulé sont respectés.
# ---------------------------------------------------------------------------
EVOLUTION = {
    "varroase": {
        "depart": 0.04, "vitesse": 0.5, "degats": 0.2, "cible": "couvain",
        "traitement": {"semaine": 4, "efficacite": 0.9, "action": "Traitement anti-varroa homologué (acide oxalique ou lanières) sur toutes les ruches du rucher."},
        "etapes": [
            (0, "Quelques varroas cachés", "Les acariens se reproduisent dans le couvain operculé. On n'en voit presque pas sur les abeilles."),
            (3, "Le seuil est dépassé", "Le comptage sur lange montre plus de varroas que le seuil. C'est le bon moment pour traiter."),
            (6, "Couvain en mosaïque", "Des cellules restent vides au milieu du couvain, certains opercules sont percés."),
            (9, "Abeilles aux ailes froissées", "Les virus transmis par le varroa apparaissent : des abeilles naissent avec des ailes déformées et rampent devant la ruche."),
            (13, "Effondrement", "La population chute très vite, le couvain disparaît. La colonie ne passera pas l'hiver."),
        ],
        "apres_traitement": [
            (4, "Traitement appliqué", "La grande majorité des varroas meurent. Les cellules perforées se vident puis sont nettoyées par les ouvrières."),
            (8, "La colonie récupère", "Le couvain redevient compact. Il reste quelques varroas : on recompte au prochain contrôle."),
        ],
    },
    "loque-americaine": {
        "depart": 0.03, "vitesse": 0.55, "degats": 0.2, "cible": "couvain",
        "traitement": {"semaine": 3, "efficacite": 0.97, "action": "Déclaration aux services vétérinaires, puis transvasement des abeilles sur cadres neufs et destruction des cadres atteints."},
        "etapes": [
            (0, "Quelques larves infectées", "Les spores sont dans la nourriture. Rien ne se voit encore sur le cadre."),
            (3, "Opercules affaissés", "Des opercules deviennent foncés, creusés et percés. Le test de l'allumette fait un fil gluant."),
            (7, "Odeur et écailles", "Le couvain est très irrégulier, une odeur de colle chaude sort de la ruche. Les larves séchées collent aux cellules."),
            (11, "Colonie perdue", "Presque plus de jeunes abeilles ne naissent. Les ruches voisines risquent d'être contaminées par pillage."),
        ],
        "apres_traitement": [
            (3, "Transvasement", "Les abeilles repartent sur des cadres neufs : tout l'ancien couvain est détruit, le cadre est vide un moment."),
            (7, "Nouveau couvain sain", "La reine pond sur la cire neuve. La colonie reste sous surveillance des services vétérinaires."),
        ],
    },
    "loque-europeenne": {
        "depart": 0.05, "vitesse": 0.42, "degats": 0.12, "cible": "couvain",
        "traitement": {"semaine": 4, "efficacite": 0.85, "action": "Retrait des cadres les plus atteints, nourrissement et, si besoin, changement de reine."},
        "etapes": [
            (0, "Larves stressées", "La bactérie profite d'un manque de nourriture ou d'un printemps difficile."),
            (4, "Larves tordues", "Dans les cellules ouvertes, des larves jaunâtres se tordent au lieu d'être bien enroulées."),
            (8, "Couvain clairsemé", "Beaucoup de larves meurent avant l'operculation. La colonie se renouvelle mal."),
            (12, "Colonie affaiblie", "La population baisse ; la colonie peut s'en remettre seule si la saison devient favorable."),
        ],
        "apres_traitement": [
            (4, "Cadres retirés", "On enlève les cadres les plus touchés et on nourrit : les larves sont mieux soignées."),
            (8, "Couvain régulier", "Les nouvelles larves sont bien blanches et enroulées."),
        ],
    },
    "nosemose": {
        "depart": 0.06, "vitesse": 0.38, "degats": 0.11, "cible": "adultes",
        "traitement": {"semaine": 3, "efficacite": 0.7, "action": "Cadres et matériel désinfectés, ruche au sec, nourrissement léger. Pas d'antibiotique autorisé."},
        "etapes": [
            (0, "Intestins infectés", "Le parasite se multiplie dans l'intestin des abeilles adultes, sans signe visible."),
            (3, "Traces brunes", "Des taches de diarrhée apparaissent sur les cadres et la planche d'envol."),
            (7, "Ouvrières épuisées", "Les abeilles vivent moins longtemps. La reine pond moins car il y a moins de nourrices."),
            (12, "Dépopulation", "La colonie s'affaiblit, surtout à la sortie de l'hiver."),
        ],
        "apres_traitement": [
            (3, "Hygiène renforcée", "Cadres souillés remplacés, ruche au sec : la contamination ralentit."),
            (7, "Remontée lente", "Les nouvelles abeilles sont saines ; les taches disparaissent peu à peu."),
        ],
    },
    "couvain-platre": {
        "depart": 0.05, "vitesse": 0.34, "degats": 0.06, "cible": "couvain",
        "traitement": {"semaine": 3, "efficacite": 0.8, "action": "Ruche aérée, cadres atteints retirés, et changement de reine si la maladie revient."},
        "etapes": [
            (0, "Spores dans le couvain", "Le champignon se développe surtout au printemps, quand il fait froid et humide."),
            (3, "Momies blanches", "Des larves durcies, blanches puis grises, comme de petits morceaux de craie, restent dans les cellules."),
            (7, "Momies sur la planche", "Les ouvrières sortent les momies : on en trouve devant la ruche."),
            (11, "Couvain réduit", "La colonie perd des générations d'abeilles mais survit souvent."),
        ],
        "apres_traitement": [
            (3, "Ruche aérée", "Moins d'humidité : le champignon se développe beaucoup moins."),
            (6, "Couvain propre", "Les ouvrières ont nettoyé les cellules ; les nouvelles larves sont saines."),
        ],
    },
    "ailes-deformees": {
        "depart": 0.04, "vitesse": 0.45, "degats": 0.15, "cible": "adultes",
        "traitement": {"semaine": 4, "efficacite": 0.8, "action": "Lutte contre le varroa, qui transmet le virus : traitement anti-varroa et suivi du taux d'infestation."},
        "etapes": [
            (0, "Virus discret", "Le virus est présent mais ne se voit pas tant qu'il y a peu de varroas."),
            (4, "Premières ailes froissées", "Des abeilles naissent avec des ailes chiffonnées et un abdomen court."),
            (8, "Rampantes devant la ruche", "Les abeilles malades ne volent pas et sont rejetées hors de la ruche."),
            (12, "Colonie qui s'éteint", "Trop d'abeilles ne peuvent plus travailler : la colonie s'effondre."),
        ],
        "apres_traitement": [
            (4, "Varroas éliminés", "Sans varroa, le virus se transmet beaucoup moins."),
            (8, "Naissances normales", "Les nouvelles abeilles ont des ailes bien formées."),
        ],
    },
    "frelon-asiatique": {
        "depart": 0.05, "vitesse": 0.42, "degats": 0.13, "cible": "butineuses",
        "traitement": {"semaine": 3, "efficacite": 0.75, "action": "Pièges sélectifs au printemps, muselière ou grille devant l'entrée, et signalement des nids pour destruction."},
        "etapes": [
            (0, "Premiers frelons", "Quelques frelons chassent en vol stationnaire devant la ruche."),
            (3, "Butineuses bloquées", "Les abeilles n'osent plus sortir : le pollen et le nectar rentrent moins."),
            (7, "Réserves vides", "Les cellules de pollen se vident, la reine pond moins."),
            (11, "Colonie trop faible", "La colonie entre en hiver avec trop peu d'abeilles et de réserves."),
        ],
        "apres_traitement": [
            (3, "Entrée protégée", "Les pièges et la muselière réduisent la pression des frelons."),
            (7, "Butinage reparti", "Les abeilles ressortent et les réserves remontent."),
        ],
    },
    "petit-coleoptere": {
        "depart": 0.03, "vitesse": 0.5, "degats": 0.15, "cible": "couvain",
        "traitement": {"semaine": 3, "efficacite": 0.8, "action": "Déclaration obligatoire aux services vétérinaires, pièges à coléoptères, colonie resserrée et forte."},
        "etapes": [
            (0, "Quelques coléoptères", "Les adultes se cachent dans les coins de la ruche."),
            (3, "Larves dans les cadres", "Les larves du coléoptère creusent les rayons et mangent pollen, miel et couvain."),
            (7, "Miel qui fermente", "Le miel coule, mousse et sent l'orange pourrie."),
            (11, "Ruche abandonnée", "Les abeilles quittent la ruche, devenue inutilisable."),
        ],
        "apres_traitement": [
            (3, "Pièges posés", "Les coléoptères sont piégés et la colonie, resserrée, défend mieux ses cadres."),
            (7, "Cadres protégés", "Plus de nouvelles galeries : les rayons sont réparés."),
        ],
    },
}


def evolution_pour(slug):
    """Paramètres de la simulation « Évolution dans la ruche » (affichage uniquement)."""
    e = EVOLUTION.get(slug)
    if not e:
        return None
    etape = lambda t: {"semaine": t[0], "titre": t[1], "texte": t[2]}
    return {
        "slug": slug,
        "effets": ANATOMIE_MALADIES.get(slug, {}).get("effets", []),
        "depart": e["depart"], "vitesse": e["vitesse"], "degats": e["degats"], "cible": e["cible"],
        "traitement": e["traitement"],
        "etapes": [etape(t) for t in e["etapes"]],
        "apres_traitement": [etape(t) for t in e["apres_traitement"]],
        "semaines": 16,
        "population": 30000,
    }
