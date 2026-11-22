from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator,EmailValidator,RegexValidator
from django.utils import timezone

def valider_date_nomination(value):
    if value < timezone.localdate():
        raise ValidationError(
            "La date de nomination ne peut pas être antérieure à la date actuelle."
        )
def validate_date_naissance(date):
    if not date:
        raise ValidationError(
            "La date de naissance est obligatoire."
        )
    today = timezone.localdate()
    if date > today:
        raise ValidationError(
            "La date de naissance ne peut pas être dans le futur."
        )
    age = today.year - date.year - ((today.month, today.day) < (date.month, date.day))
    if age < 10:
        raise ValidationError(
            "L'utilisateur doit avoir au moins 10 ans."
        )
    if age > 120:
        raise ValidationError(
            "Veuillez entrer une date de naissance réaliste."
        )
    
class Utilisateur(AbstractUser):
    username = models.CharField(max_length=150,unique=True,validators=[MinLengthValidator(4)])
    email = models.EmailField(unique=True,validators=[EmailValidator()])
    sexe = models.CharField(max_length=5,choices=[("homme","Homme"),("femme","Femme")])
    date_naissance = models.DateField(validators=[validate_date_naissance])
    role = models.CharField(max_length=20, choices=[("admin","Administrateur"),("apiculteur","Apiculteur"),("responsable","Responsable production et stock")])
    statut = models.CharField(max_length=10,choices=[("actif", "Actif"),("inactif", "Inactif"),("suspendu", "Suspendu")],default="actif")
    telephone = models.CharField(unique=True,max_length=13,validators=[RegexValidator(regex=r'^\+?[0-9]{8,12}$',message="Veuillez saisir un numéro de téléphone valide.")])
    face_encoding = models.TextField(null=True, blank=True)
    face_configured = models.BooleanField(default=False)
    profil_comportemental = models.JSONField(null=True, blank=True)
    premiere_connexion = models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    REQUIRED_FIELDS = ['role','email']

    def __str__(self):
        return self.username

class Admin(Utilisateur):
    date_nomination = models.DateField(null=True, blank=True, validators=[valider_date_nomination])
    def clean(self):
        super().clean()

        if self.date_nomination:
            if self.created_at:
                date_reference = self.created_at.date()
            else:
                date_reference = timezone.localdate()

            if self.date_nomination < date_reference:
                raise ValidationError(
                    "La date de nomination doit être supérieure ou égale à la date de création du compte."
                )  
    def save(self, *args, **kwargs):
        self.role = 'admin'
        super().save(*args, **kwargs)

class Apiculteur(Utilisateur):
    specialite = models.CharField(max_length=100, null=True, blank=True,validators=[MinLengthValidator(3)])
    def save(self, *args, **kwargs):
        self.role = 'apiculteur'
        super().save(*args, **kwargs)

class Responsable(Utilisateur):
    niveau_experience = models.CharField(max_length=20, choices=[("debutant", "Débutant"),("intermediaire", "Intermédiaire"),("experimente", "Expérimenté"),], null=True, blank=True)
    def save(self, *args, **kwargs):
        self.role = 'responsable'
        super().save(*args, **kwargs)
