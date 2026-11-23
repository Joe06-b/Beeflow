from collections import defaultdict
from io import BytesIO
from math import cos, pi, sin

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import EtatPredit, TypeRuche


PROPOLIS = colors.HexColor("#2B1B0F")
BROWN = colors.HexColor("#5E3B20")
HONEY = colors.HexColor("#E9B949")
WAX = colors.HexColor("#FFF9ED")
LINE = colors.HexColor("#E7D9C1")
MUTED = colors.HexColor("#7A6A5B")
GOOD = colors.HexColor("#3F7A4A")
GOOD_BG = colors.HexColor("#E8F3E9")
WARN = colors.HexColor("#9A6700")
WARN_BG = colors.HexColor("#FFF3D2")
BAD = colors.HexColor("#A93C30")
BAD_BG = colors.HexColor("#FBE9E6")
WHITE = colors.white


def _dessiner_logo(canvas, x, y, taille):
    """Dessine le logo BeeFlow vectoriel dans le rapport."""
    canvas.saveState()
    rayon = taille / 2
    centre_x = x + rayon
    centre_y = y + rayon
    points = []
    for index in range(6):
        angle = pi / 6 + index * pi / 3
        points.extend((centre_x + rayon * cos(angle), centre_y + rayon * sin(angle)))
    chemin = canvas.beginPath()
    chemin.moveTo(points[0], points[1])
    for index in range(2, len(points), 2):
        chemin.lineTo(points[index], points[index + 1])
    chemin.close()
    canvas.setFillColor(HONEY)
    canvas.drawPath(chemin, fill=1, stroke=0)
    canvas.setFillColor(WAX)
    canvas.ellipse(x + taille * .27, y + taille * .60, x + taille * .48, y + taille * .75, fill=1, stroke=0)
    canvas.ellipse(x + taille * .52, y + taille * .60, x + taille * .73, y + taille * .75, fill=1, stroke=0)
    canvas.setFillColor(PROPOLIS)
    canvas.ellipse(x + taille * .34, y + taille * .20, x + taille * .66, y + taille * .66, fill=1, stroke=0)
    canvas.setStrokeColor(HONEY)
    canvas.setLineWidth(max(1.2, taille * .06))
    canvas.line(x + taille * .36, y + taille * .38, x + taille * .64, y + taille * .38)
    canvas.line(x + taille * .38, y + taille * .50, x + taille * .62, y + taille * .50)
    canvas.restoreState()


def _entete_pied_de_page(canvas, document):
    largeur, hauteur = landscape(A4)
    canvas.saveState()
    canvas.setTitle(document.title)
    canvas.setAuthor("BeeFlow")
    canvas.setFillColor(PROPOLIS)
    canvas.rect(0, hauteur - 29 * mm, largeur, 29 * mm, fill=1, stroke=0)
    _dessiner_logo(canvas, 13 * mm, hauteur - 23 * mm, 14 * mm)
    canvas.setFont("Helvetica-Bold", 23)
    canvas.setFillColor(HONEY)
    canvas.drawString(31 * mm, hauteur - 14 * mm, "Bee")
    canvas.setFillColor(WAX)
    canvas.drawString(46 * mm, hauteur - 14 * mm, "Flow")
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#DCC9AE"))
    canvas.drawString(31 * mm, hauteur - 20 * mm, "Gestion intelligente des ruches")
    canvas.setFillColor(WAX)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawRightString(largeur - 13 * mm, hauteur - 12 * mm, document.report_title)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#DCC9AE"))
    canvas.drawRightString(largeur - 13 * mm, hauteur - 19 * mm, document.report_date)
    canvas.setStrokeColor(LINE)
    canvas.line(13 * mm, 12 * mm, largeur - 13 * mm, 12 * mm)
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(13 * mm, 7 * mm, "BeeFlow - Rapport de gestion des ruches")
    canvas.drawRightString(largeur - 13 * mm, 7 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _format_nombre(valeur):
    return f"{valeur:,}".replace(",", " ")


def _couleurs_etat(etat):
    return {
        EtatPredit.BON: (GOOD_BG, GOOD),
        EtatPredit.A_SURVEILLER: (WARN_BG, WARN),
        EtatPredit.RISQUE_ELEVE: (BAD_BG, BAD),
    }.get(etat, (WARN_BG, WARN))


def generer_pdf_ruches(ruches, regroupement="type"):
    ruches = list(ruches)
    regroupement = "etat" if regroupement == "etat" else "type"
    libelle_regroupement = "état" if regroupement == "etat" else "type"
    date_rapport = timezone.localdate()
    groupes = defaultdict(list)
    for ruche in ruches:
        cle = ruche.etat_predit if regroupement == "etat" else ruche.type_ruche
        groupes[cle or "Non renseigné"].append(ruche)

    if regroupement == "etat":
        ordre = [EtatPredit.BON, EtatPredit.A_SURVEILLER, EtatPredit.RISQUE_ELEVE]
        libelles = dict(EtatPredit.choices)
        cles = [cle for cle in ordre if cle in groupes]
        cles.extend(sorted(cle for cle in groupes if cle not in ordre))
    else:
        libelles = dict(TypeRuche.choices)
        cles = sorted(groupes, key=lambda cle: libelles.get(cle, cle).lower())

    flux = BytesIO()
    document = SimpleDocTemplate(
        flux,
        pagesize=landscape(A4),
        leftMargin=13 * mm,
        rightMargin=13 * mm,
        topMargin=36 * mm,
        bottomMargin=18 * mm,
        title=f"BeeFlow - Ruches par {libelle_regroupement}",
        author="BeeFlow",
    )
    document.report_title = f"Rapport des ruches par {libelle_regroupement}"
    document.report_date = f"Généré le {date_rapport:%d/%m/%Y} - Afrique/Tunis"
    titre_style = ParagraphStyle("Titre", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=PROPOLIS, alignment=TA_LEFT, spaceAfter=4 * mm)
    texte_style = ParagraphStyle("Texte", fontName="Helvetica", fontSize=9.5, leading=14, textColor=MUTED, alignment=TA_LEFT)
    groupe_style = ParagraphStyle("Groupe", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=PROPOLIS)

    histoire = [
        Paragraph("Inventaire des ruches", titre_style),
        Paragraph(
            f"Document regroupé par {libelle_regroupement}. Vert : Bon, jaune : À surveiller, rouge : Risque élevé.",
            texte_style,
        ),
        Spacer(1, 5 * mm),
    ]
    total_population = sum(ruche.nombre_abeilles for ruche in ruches)
    avec_reine = sum(1 for ruche in ruches if ruche.presence_reine)
    cartes = Table(
        [[
            Paragraph(f"<b>{len(ruches)}</b><br/><font size='9' color='#7A6A5B'>Ruches exportées</font>", titre_style),
            Paragraph(f"<b>{_format_nombre(total_population)}</b><br/><font size='9' color='#7A6A5B'>Abeilles estimées</font>", titre_style),
            Paragraph(f"<b>{avec_reine}</b><br/><font size='9' color='#7A6A5B'>Ruches avec reine</font>", titre_style),
        ]],
        colWidths=[63 * mm, 63 * mm, 63 * mm],
        rowHeights=[21 * mm],
        hAlign="LEFT",
    )
    cartes.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WAX),
        ("BOX", (0, 0), (-1, -1), .7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), .7, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    histoire.extend([cartes, Spacer(1, 7 * mm)])
    if not ruches:
        histoire.append(Paragraph("Aucune ruche n'est enregistrée pour le moment.", texte_style))

    entetes = ["Code", "Type", "Race", "Installation", "Reine", "Population", "État", "user_id", "idZone"]
    largeurs = [24, 28, 32, 26, 18, 25, 31, 21, 21]
    largeurs = [largeur * mm for largeur in largeurs]
    for cle in cles:
        ruches_groupe = sorted(groupes[cle], key=lambda ruche: ruche.code_ruche)
        libelle = libelles.get(cle, cle)
        fond_groupe, texte_groupe = _couleurs_etat(cle) if regroupement == "etat" else (colors.HexColor("#F6EBD3"), BROWN)
        bandeau = Table([[Paragraph(str(libelle), groupe_style), f"{len(ruches_groupe)} ruche(s)"]], colWidths=[169 * mm, 27 * mm], hAlign="LEFT")
        bandeau.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), fond_groupe),
            ("TEXTCOLOR", (0, 0), (-1, -1), texte_groupe),
            ("BOX", (0, 0), (-1, -1), .8, texte_groupe),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (1, 0), (1, 0), 9),
        ]))
        lignes = [entetes]
        for ruche in ruches_groupe:
            lignes.append([
                ruche.code_ruche, ruche.type_ruche, ruche.race_abeilles,
                ruche.date_installation.strftime("%d/%m/%Y"),
                "Oui" if ruche.presence_reine else "Non",
                _format_nombre(ruche.nombre_abeilles), ruche.get_etat_predit_display(),
                ruche.user_id if ruche.user_id is not None else "-",
                ruche.idZone if ruche.idZone is not None else "-",
            ])
        tableau = Table(lignes, colWidths=largeurs, repeatRows=1, hAlign="LEFT")
        style_tableau = [
            ("BACKGROUND", (0, 0), (-1, 0), PROPOLIS),
            ("TEXTCOLOR", (0, 0), (-1, 0), HONEY),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (4, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), .45, LINE),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ]
        for numero, ruche in enumerate(ruches_groupe, start=1):
            style_tableau.append(("BACKGROUND", (0, numero), (-1, numero), WHITE if numero % 2 else WAX))
            fond_etat, texte_etat = _couleurs_etat(ruche.etat_predit)
            style_tableau.extend([
                ("BACKGROUND", (6, numero), (6, numero), fond_etat),
                ("TEXTCOLOR", (6, numero), (6, numero), texte_etat),
                ("FONTNAME", (6, numero), (6, numero), "Helvetica-Bold"),
                ("BACKGROUND", (4, numero), (4, numero), GOOD_BG if ruche.presence_reine else BAD_BG),
                ("TEXTCOLOR", (4, numero), (4, numero), GOOD if ruche.presence_reine else BAD),
                ("FONTNAME", (4, numero), (4, numero), "Helvetica-Bold"),
            ])
        tableau.setStyle(TableStyle(style_tableau))
        histoire.extend([KeepTogether([bandeau, Spacer(1, 2 * mm)]), tableau, Spacer(1, 6 * mm)])

    document.build(histoire, onFirstPage=_entete_pied_de_page, onLaterPages=_entete_pied_de_page)
    return flux.getvalue()
