from datetime import date

from django.core.exceptions import ValidationError
from django.db import models


class EtatSante(models.TextChoices):
    """<<enumeration>> EtatSante"""
    BON = "Bon", "Bon"
    MOYEN = "Moyen", "Moyen"
    CRITIQUE = "Critique", "Critique"


class NiveauRisque(models.TextChoices):
    """<<enumeration>> NiveauRisque"""
    FAIBLE = "Faible", "Faible"
    MOYEN = "Moyen", "Moyen"
    ELEVE = "Eleve", "Élevé"


class SuiviSanitaire(models.Model):
    # - id_suivi : int
    id_suivi = models.AutoField(primary_key=True)

    # - ruche : association "Avoir" : 1 Ruche  ---  0..* SuiviSanitaire
    # Clé étrangère vers la Ruche de rucheapp. La colonne en base reste "id_ruche"
    # (même nom que dans le diagramme de classes). Supprimer une ruche supprime ses suivis.
    ruche = models.ForeignKey(
        "rucheapp.Ruche",
        on_delete=models.CASCADE,
        related_name="suivis",
        db_column="id_ruche",
        verbose_name="Ruche",
    )

    # - date_suivi : Date
    date_suivi = models.DateField(default=date.today, verbose_name="Date du suivi")

    # - etat_sante : EtatSante
    etat_sante = models.CharField(
        max_length=10,
        choices=EtatSante.choices,
        default=EtatSante.BON,
        verbose_name="État de santé",
    )

    # - maladie_detectee : String
    maladie_detectee = models.CharField(
        max_length=150, blank=True, verbose_name="Maladie détectée"
    )

    # - symptomes : String
    symptomes = models.TextField(blank=True, verbose_name="Symptômes")

    # - observation : String
    observation = models.TextField(blank=True, verbose_name="Observation")

    # - type_traitement : String
    type_traitement = models.CharField(
        max_length=150, blank=True, verbose_name="Type de traitement"
    )

    # - dose : String
    dose = models.CharField(max_length=100, blank=True, verbose_name="Dose")

    # - date_traitement : Date
    date_traitement = models.DateField(
        null=True, blank=True, verbose_name="Date du traitement"
    )

    # - date_prochain_controle : Date
    date_prochain_controle = models.DateField(
        null=True, blank=True, verbose_name="Date du prochain contrôle"
    )

    # - niveau_risque : NiveauRisque
    niveau_risque = models.CharField(
        max_length=10,
        choices=NiveauRisque.choices,
        default=NiveauRisque.FAIBLE,
        verbose_name="Niveau de risque",
    )

    class Meta:
        db_table = "suivi_sanitaire"
        verbose_name = "Suivi sanitaire"
        verbose_name_plural = "Suivis sanitaires"
        ordering = ["-date_suivi", "-id_suivi"]

    def __str__(self):
        return f"Suivi #{self.id_suivi} – Ruche {self.ruche} – {self.date_suivi}"

    # ---------- Règles de validation (appelées par les formulaires / full_clean) ----------
    def clean(self):
        errors = {}

        if self.date_suivi and self.date_suivi > date.today():
            errors["date_suivi"] = "La date du suivi ne peut pas être dans le futur."

        if self.date_traitement and self.date_suivi and self.date_traitement < self.date_suivi:
            errors["date_traitement"] = "La date du traitement doit être postérieure ou égale à la date du suivi."

        if self.date_prochain_controle and self.date_suivi and self.date_prochain_controle <= self.date_suivi:
            errors["date_prochain_controle"] = "Le prochain contrôle doit être après la date du suivi."

        # Un traitement saisi doit avoir une dose et une date
        if self.type_traitement and not self.dose:
            errors["dose"] = "Indiquez la dose du traitement."
        if self.type_traitement and not self.date_traitement:
            errors["date_traitement"] = "Indiquez la date du traitement."

        # Une ruche en état critique ne peut pas être classée à risque faible
        if self.etat_sante == EtatSante.CRITIQUE and self.niveau_risque == NiveauRisque.FAIBLE:
            errors["niveau_risque"] = "Un état critique ne peut pas avoir un risque faible."

        if errors:
            raise ValidationError(errors)

    # ---------- Propriétés utiles pour consulterAlertes() ----------
    @property
    def est_critique(self):
        return self.etat_sante == EtatSante.CRITIQUE or self.niveau_risque == NiveauRisque.ELEVE

    @property
    def est_remplace(self):
        """Vrai si un suivi PLUS RÉCENT existe pour la même ruche.
        Dans ce cas, le contrôle prévu par ce suivi a déjà été fait : il ne doit plus créer d'alerte.
        (Dans les listes, la valeur est calculée d'avance en une seule requête par services.avec_remplace().)"""
        if getattr(self, "_remplace", None) is None and getattr(self, "remplace", None) is not None:
            self._remplace = self.remplace           # valeur annotée par services.avec_remplace()
        if getattr(self, "_remplace", None) is None:
            self._remplace = (
                SuiviSanitaire.objects.filter(ruche_id=self.ruche_id)
                .filter(models.Q(date_suivi__gt=self.date_suivi)
                        | models.Q(date_suivi=self.date_suivi, id_suivi__gt=self.id_suivi))
                .exists()
            )
        return self._remplace

    @property
    def controle_en_retard(self):
        return bool(self.date_prochain_controle and self.date_prochain_controle < date.today()
                    and not self.est_remplace)

    @property
    def jours_avant_controle(self):
        if not self.date_prochain_controle:
            return None
        return (self.date_prochain_controle - date.today()).days

    @property
    def jours_de_retard(self):
        if not self.controle_en_retard:
            return 0
        return (date.today() - self.date_prochain_controle).days

    @property
    def est_en_alerte(self):
        # Seul le DERNIER suivi d'une ruche compte : un ancien suivi critique déjà suivi d'un autre n'alerte plus
        return (self.est_critique and not self.est_remplace) or self.controle_en_retard
