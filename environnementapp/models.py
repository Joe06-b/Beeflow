from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TypeVegetation(models.TextChoices):
    """<<enumeration>> TypeVegetation"""
    FORET = "Foret", "Forêt"
    PRAIRIE = "Prairie", "Prairie"
    CULTURE = "Culture", "Culture"
    VERGER = "Verger", "Verger"
    MAQUIS = "Maquis", "Maquis"
    AUTRE = "Autre", "Autre"


class NiveauFloraison(models.TextChoices):
    """<<enumeration>> niveauFloraison"""
    ABSENTE = "Absente", "Absente"
    FAIBLE = "Faible", "Faible"
    MOYENNE = "Moyenne", "Moyenne"
    ABONDANTE = "Abondante", "Abondante"


class NiveauRisque(models.TextChoices):
    """<<enumeration>> niveauRisque"""
    FAIBLE = "Faible", "Faible"
    MOYEN = "Moyen", "Moyen"
    ELEVE = "Eleve", "Élevé"
    CRITIQUE = "Critique", "Critique"


class Environnement(models.Model):
    """
    Classe principale représentant une zone géographique où sont installées les ruches.
    Conforme au diagramme de classes UML.
    """
    # - idZone : int
    idZone = models.AutoField(primary_key=True, verbose_name="Identifiant de la zone")

    # - nomZone : String
    nomZone = models.CharField(max_length=150, verbose_name="Nom de la zone")

    # - latitude : double
    latitude = models.FloatField(verbose_name="Latitude (°)")

    # - longitude : double
    longitude = models.FloatField(verbose_name="Longitude (°)")

    # - typeVegetation : String (<<enumeration>> TypeVegetation)
    typeVegetation = models.CharField(
        max_length=20,
        choices=TypeVegetation.choices,
        default=TypeVegetation.PRAIRIE,
        verbose_name="Type de végétation",
    )

    # - surface : double (en hectares)
    surface = models.FloatField(verbose_name="Surface (ha)")

    # - temperature : double (en °C)
    temperature = models.FloatField(verbose_name="Température (°C)")

    # - humidite : double (en %)
    humidite = models.FloatField(verbose_name="Humidité (%)")

    # - precipitation : double (en mm)
    precipitation = models.FloatField(default=0.0, verbose_name="Précipitations (mm)")

    # - vitesseVent : double (en km/h)
    vitesseVent = models.FloatField(default=0.0, verbose_name="Vitesse du vent (km/h)")

    # - niveauFloraison : String (<<enumeration>> niveauFloraison)
    niveauFloraison = models.CharField(
        max_length=20,
        choices=NiveauFloraison.choices,
        default=NiveauFloraison.MOYENNE,
        verbose_name="Niveau de floraison",
    )

    # - dateMesure : DateTime
    dateMesure = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date et heure de mesure",
    )

    # - niveauRisque : String (<<enumeration>> niveauRisque)
    # Conservé conformément à l'UML, non calculé/modifié automatiquement à l'étape 1
    niveauRisque = models.CharField(
        max_length=20,
        choices=NiveauRisque.choices,
        default=NiveauRisque.FAIBLE,
        blank=True,
        verbose_name="Niveau de risque",
    )

    # - scoreQualite : double
    # Conservé conformément à l'UML, non calculé/modifié automatiquement à l'étape 1
    scoreQualite = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Score de qualité",
    )

    class Meta:
        db_table = "environnement"
        verbose_name = "Environnement"
        verbose_name_plural = "Environnements"
        ordering = ["-dateMesure", "-idZone"]

    def __str__(self):
        return f"{self.nomZone} (#{self.idZone}) – {self.get_typeVegetation_display()}"

    # ---------- Règles de validation (appelées par les formulaires / full_clean) ----------
    def clean(self):
        errors = {}

        if self.surface is not None and self.surface <= 0:
            errors["surface"] = "La surface doit être strictement positive (> 0 ha)."

        if self.latitude is not None and (self.latitude < -90 or self.latitude > 90):
            errors["latitude"] = "La latitude doit être comprise entre -90° et 90°."

        if self.longitude is not None and (self.longitude < -180 or self.longitude > 180):
            errors["longitude"] = "La longitude doit être comprise entre -180° et 180°."

        if self.humidite is not None and (self.humidite < 0 or self.humidite > 100):
            errors["humidite"] = "L'humidité doit être comprise entre 0% et 100%."

        if self.precipitation is not None and self.precipitation < 0:
            errors["precipitation"] = "Les précipitations ne peuvent pas être négatives."

        if self.vitesseVent is not None and self.vitesseVent < 0:
            errors["vitesseVent"] = "La vitesse du vent ne peut pas être négative."

        if self.dateMesure and self.dateMesure > timezone.now():
            errors["dateMesure"] = "La date de mesure ne peut pas être dans le futur."

        if errors:
            raise ValidationError(errors)
