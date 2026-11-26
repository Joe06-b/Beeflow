import re
import uuid
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class EtatPredit(models.TextChoices):
    """Etat prédit de la ruche, conformément au diagramme de classes."""

    BON = "Bon", "Bon"
    A_SURVEILLER = "A_Surveiller", "À surveiller"
    RISQUE_ELEVE = "Risque_Eleve", "Risque élevé"


class TypeRuche(models.TextChoices):
    DADANT = "Dadant", "Dadant"
    LANGSTROTH = "Langstroth", "Langstroth"
    WARRE = "Warre", "Warré"
    KENYANE = "Kenyane", "Kényane"
    TRADITIONNELLE = "Traditionnelle", "Traditionnelle"
    AUTRE = "Autre", "Autre"


class RaceAbeilles(models.TextChoices):
    NOIRE = "Noire", "Abeille noire"
    BUCKFAST = "Buckfast", "Buckfast"
    ITALIENNE = "Italienne", "Italienne"
    CARNOLIENNE = "Carnolienne", "Carnolienne"
    CAUCASIENNE = "Caucasienne", "Caucasienne"
    AFRICAINE = "Africaine", "Africaine"
    AUTRE = "Autre", "Autre"


class Ruche(models.Model):
    id_ruche = models.AutoField(primary_key=True)
    # Identifiant public immuable utilise par les QR.
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    code_ruche = models.CharField(max_length=30, unique=True, verbose_name="Code de la ruche")
    type_ruche = models.CharField(max_length=80, verbose_name="Type de ruche")
    race_abeilles = models.CharField(max_length=100, verbose_name="Race des abeilles")
    date_installation = models.DateField(verbose_name="Date d'installation")
    presence_reine = models.BooleanField(default=True, verbose_name="Présence de la reine")
    nombre_abeilles = models.PositiveIntegerField(verbose_name="Nombre d'abeilles")
    etat_predit = models.CharField(
        max_length=20,
        choices=EtatPredit.choices,
        default=EtatPredit.BON,
        verbose_name="État prédit",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ruches",
        db_column="user_id",
        verbose_name="ID utilisateur",
    )
    # L'environnement reste un identifiant optionnel tant que le module de
    # l'équipe ne fournit pas encore son modèle définitif.
    idZone = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="idZone",
    )

    class Meta:
        db_table = "ruche"
        ordering = ["code_ruche"]
        verbose_name = "Ruche"
        verbose_name_plural = "Ruches"

    def __str__(self):
        return self.code_ruche

    @property
    def etat_css(self):
        return {
            EtatPredit.BON: "rch-state-bon",
            EtatPredit.A_SURVEILLER: "rch-state-surveillance",
            EtatPredit.RISQUE_ELEVE: "rch-state-risque",
        }.get(self.etat_predit, "rch-state-surveillance")

    @property
    def type_label(self):
        return dict(TypeRuche.choices).get(self.type_ruche, self.type_ruche)

    @property
    def race_label(self):
        return dict(RaceAbeilles.choices).get(self.race_abeilles, self.race_abeilles)

    def valeurs_historiques(self):
        """Retourne un instantané lisible et sérialisable de la ruche."""
        return {
            "code_ruche": self.code_ruche,
            "type_ruche": self.type_label,
            "race_abeilles": self.race_label,
            "date_installation": self.date_installation.strftime("%d/%m/%Y"),
            "presence_reine": "Oui" if self.presence_reine else "Non",
            "nombre_abeilles": self.nombre_abeilles,
            "etat_predit": self.get_etat_predit_display(),
            "user_id": self.user_id if self.user_id is not None else "Non renseigné",
            "idZone": self.idZone if self.idZone is not None else "Non renseigné",
        }

    def clean(self):
        errors = {}
        self.code_ruche = (self.code_ruche or "").strip().upper()
        self.type_ruche = (self.type_ruche or "").strip()
        self.race_abeilles = (self.race_abeilles or "").strip()

        if not re.fullmatch(r"[A-Z0-9-]+", self.code_ruche):
            errors["code_ruche"] = "Utilisez uniquement des lettres, chiffres et tirets."
        if self.date_installation and self.date_installation > date.today():
            errors["date_installation"] = "La date d'installation ne peut pas être dans le futur."
        if self.nombre_abeilles is not None and not 1 <= self.nombre_abeilles <= 2_000_000:
            errors["nombre_abeilles"] = "La population doit être comprise entre 1 et 2 000 000."
        if self.race_abeilles and any(caractere.isdigit() for caractere in self.race_abeilles):
            errors["race_abeilles"] = "La race des abeilles ne doit pas contenir de chiffre."

        if errors:
            raise ValidationError(errors)


class ActionHistorique(models.TextChoices):
    AJOUT = "ajout", "Ajout"
    MODIFICATION = "modification", "Modification"
    SUPPRESSION = "suppression", "Suppression"


class HistoriqueRuche(models.Model):
    LIBELLES_CHAMPS = {
        "code_ruche": "Code de la ruche",
        "type_ruche": "Type de ruche",
        "race_abeilles": "Race des abeilles",
        "date_installation": "Date d'installation",
        "presence_reine": "Présence de la reine",
        "nombre_abeilles": "Nombre d'abeilles",
        "etat_predit": "État prédit",
        "user_id": "Utilisateur",
        "idZone": "Environnement",
    }

    ruche = models.ForeignKey(
        Ruche,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="historiques",
        verbose_name="Ruche",
    )
    code_ruche = models.CharField(max_length=30, db_index=True)
    action = models.CharField(max_length=20, choices=ActionHistorique.choices, db_index=True)
    changements = models.JSONField(default=dict, blank=True)
    donnees = models.JSONField(default=dict, blank=True)
    auteur = models.CharField(max_length=150, default="Système")
    date_modification = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "historique_ruche"
        ordering = ["-date_modification", "-pk"]
        verbose_name = "Historique de ruche"
        verbose_name_plural = "Historiques des ruches"

    def __str__(self):
        return f"{self.code_ruche} - {self.get_action_display()}"

    @classmethod
    def enregistrer(cls, ruche, action, avant=None, apres=None, auteur="Système"):
        avant = avant or {}
        apres = apres or {}
        changements = {}
        for champ in cls.LIBELLES_CHAMPS:
            ancienne_valeur = avant.get(champ)
            nouvelle_valeur = apres.get(champ)
            if ancienne_valeur != nouvelle_valeur:
                changements[champ] = {
                    "label": cls.LIBELLES_CHAMPS[champ],
                    "avant": ancienne_valeur,
                    "apres": nouvelle_valeur,
                }

        if action == ActionHistorique.MODIFICATION and not changements:
            return None

        return cls.objects.create(
            ruche=ruche,
            code_ruche=apres.get("code_ruche") or avant.get("code_ruche") or ruche.code_ruche,
            action=action,
            changements=changements,
            donnees=apres or avant,
            auteur=auteur or "Système",
        )
