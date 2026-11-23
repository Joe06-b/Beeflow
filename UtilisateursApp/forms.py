import re
import secrets
import string
import threading
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm, SetPasswordForm, AuthenticationForm
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import Utilisateur, Admin, Apiculteur, Responsable
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import transaction


def envoyer_email_identifiants(utilisateur, mot_de_passe):
    sujet = "Bienvenue sur BeeFlow"

    message = f"""
Bonjour {utilisateur.first_name},

Votre compte BeeFlow a été créé avec succès.

Voici vos identifiants de connexion :

Nom d'utilisateur : {utilisateur.username}
Mot de passe : {mot_de_passe}

Cordialement,
L'équipe BeeFlow
"""
    try:
        send_mail(
            sujet,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [utilisateur.email],
            fail_silently=False
        )
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email à {utilisateur.email} : {e}")


class UtilisateurCreationForm(forms.ModelForm):

    sexe = forms.ChoiceField(
        choices=[("", "Sélectionnez le sexe"), ("homme", "Homme"), ("femme", "Femme")],
        required=True,
        label="Sexe",
        error_messages={'required': "Veuillez sélectionner le sexe."}
    )

    date_naissance = forms.DateField(
        required=True,
        label="Date de naissance",
        widget=forms.DateInput(attrs={'type': 'date'}),
        error_messages={'required': "La date de naissance est obligatoire."}
    )

    telephone = forms.CharField(
        required=True,
        label="Numéro de téléphone",
        max_length=13,
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': 'Ex: +21612345678 ou 20207883'}),
        error_messages={'required': "Le numéro de téléphone est obligatoire."}
    )

    date_nomination = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    specialite = forms.CharField(
        required=False,
        max_length=100
    )

    niveau_experience = forms.ChoiceField(
        required=False,
        choices=[
            ("", "---------"),
            ("debutant", "Débutant"),
            ("intermediaire", "Intermédiaire"),
            ("experimente", "Expérimenté")
        ]
    )

    class Meta:
        model = Utilisateur
        fields = (
            'username',
            'first_name',
            'last_name',
            'date_naissance',
            'email',
            'telephone',
            'role',
            'sexe',
            'statut'
        )

    class Media:
        js = ('js/Utilisateurs/utilisateur_role.js',)

    def clean_sexe(self):
        sexe = self.cleaned_data.get('sexe')
        if not sexe:
            raise forms.ValidationError("Veuillez sélectionner le sexe.")
        if sexe not in ['homme', 'femme']:
            raise forms.ValidationError("Le sexe sélectionné est invalide.")
        return sexe

    def clean_date_naissance(self):
        date = self.cleaned_data.get('date_naissance')
        if not date:
            raise forms.ValidationError("La date de naissance est obligatoire.")
        today = timezone.localdate()
        if date > today:
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        age = today.year - date.year - ((today.month, today.day) < (date.month, date.day))
        if age < 10:
            raise forms.ValidationError("L'utilisateur doit avoir au moins 10 ans.")
        if age > 120:
            raise forms.ValidationError("Veuillez entrer une date de naissance réaliste.")
        return date

    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone:
            raise forms.ValidationError("Le numéro de téléphone est obligatoire.")
        telephone = telephone.replace(" ", "").strip()
        if not re.match(r'^\+?[0-9]{8,12}$', telephone):
            raise forms.ValidationError("Veuillez saisir un numéro de téléphone valide (8 à 12 chiffres, ex: +21612345678 ou 12345678).")
        if Utilisateur.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà associé à un autre compte.")
        return telephone

    def clean_date_nomination(self):
        date = self.cleaned_data.get('date_nomination')

        if date and date < timezone.localdate():
            raise forms.ValidationError(
                "La date de nomination ne peut pas être antérieure à la date actuelle."
            )

        return date
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        date_nomination = cleaned_data.get('date_nomination')
        specialite = cleaned_data.get('specialite')
        niveau_experience = cleaned_data.get('niveau_experience')

        if role == 'admin':
            if specialite:
                self.add_error(
                    'specialite',
                    "La spécialité concerne uniquement les apiculteurs."
                )
            if niveau_experience:
                self.add_error(
                    'niveau_experience',
                    "Le niveau d'expérience concerne uniquement les responsables."
                )

        elif role == 'apiculteur':
            if date_nomination:
                self.add_error(
                    'date_nomination',
                    "La date de nomination concerne uniquement les administrateurs."
                )
            if niveau_experience:
                self.add_error(
                    'niveau_experience',
                    "Le niveau d'expérience concerne uniquement les responsables."
                )

        elif role == 'responsable':
            if date_nomination:
                self.add_error(
                    'date_nomination',
                    "La date de nomination concerne uniquement les administrateurs."
                )
            if specialite:
                self.add_error(
                    'specialite',
                    "La spécialité concerne uniquement les apiculteurs."
                )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        utilisateur = forms.ModelForm.save(self, commit=False)

        caracteres = string.ascii_letters + string.digits + "!@#$%&*"
        mot_de_passe = ''.join(
            secrets.choice(caracteres) for _ in range(14)
        )

        utilisateur.set_password(mot_de_passe)

        if commit:
            utilisateur.save()
            self.save_m2m()

            # Envoi du mail en arrière-plan pour ne pas bloquer la redirection de l'utilisateur
            transaction.on_commit(
                lambda: threading.Thread(
                    target=envoyer_email_identifiants,
                    args=(utilisateur, mot_de_passe),
                    daemon=True,
                ).start()
            )

        return utilisateur



class UtilisateurChangeForm(UserChangeForm):

    sexe = forms.ChoiceField(
        choices=[("", "Sélectionnez le sexe"), ("homme", "Homme"), ("femme", "Femme")],
        required=True,
        label="Sexe",
        error_messages={'required': "Veuillez sélectionner le sexe."}
    )

    date_naissance = forms.DateField(
        required=True,
        label="Date de naissance",
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date'}
        ),
        error_messages={'required': "La date de naissance est obligatoire."}
    )

    telephone = forms.CharField(
        required=True,
        label="Numéro de téléphone",
        max_length=13,
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': 'Ex: +21612345678 ou 20207883'}),
        error_messages={'required': "Le numéro de téléphone est obligatoire."}
    )

    date_nomination = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date'}
        )
    )
    specialite = forms.CharField(
        required=False,
        max_length=100
    )

    niveau_experience = forms.ChoiceField(
        required=False,
        choices=[
            ("", "---------"),
            ("debutant", "Débutant"),
            ("intermediaire", "Intermédiaire"),
            ("experimente", "Expérimenté"),
        ]
    )

    class Meta(UserChangeForm.Meta):
        model = Utilisateur
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'sexe',
            'date_naissance',
            'telephone',
            'role',
            'statut',
            'date_nomination',
            'specialite',
            'niveau_experience',
        )

    class Media:
        js = ('js/Utilisateurs/utilisateur_role.js',)

    def clean_sexe(self):
        sexe = self.cleaned_data.get('sexe')
        if not sexe:
            raise forms.ValidationError("Veuillez sélectionner le sexe.")
        if sexe not in ['homme', 'femme']:
            raise forms.ValidationError("Le sexe sélectionné est invalide.")
        return sexe

    def clean_date_naissance(self):
        date = self.cleaned_data.get('date_naissance')
        if not date:
            raise forms.ValidationError("La date de naissance est obligatoire.")
        today = timezone.localdate()
        if date > today:
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        age = today.year - date.year - ((today.month, today.day) < (date.month, date.day))
        if age < 10:
            raise forms.ValidationError("L'utilisateur doit avoir au moins 10 ans.")
        if age > 120:
            raise forms.ValidationError("Veuillez entrer une date de naissance réaliste.")
        return date

    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone:
            raise forms.ValidationError("Le numéro de téléphone est obligatoire.")
        telephone = telephone.replace(" ", "").strip()
        if not re.match(r'^\+?[0-9]{8,12}$', telephone):
            raise forms.ValidationError("Veuillez saisir un numéro de téléphone valide (8 à 12 chiffres, ex: +21612345678 ou 12345678).")
        qs = Utilisateur.objects.filter(telephone=telephone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà associé à un autre compte.")
        return telephone

    def clean_date_nomination(self):
        date = self.cleaned_data.get('date_nomination')

        if date and self.instance.created_at:
            date_creation = timezone.localtime(self.instance.created_at).date()

            if date < date_creation:
                raise forms.ValidationError(
                    "La date de nomination ne peut pas être antérieure à la date de création du compte."
                )

        return date

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password', None)
        utilisateur = self.instance

        if not utilisateur or not utilisateur.pk:
            return

        # Préremplissage selon le rôle
        if utilisateur.role == 'admin':
            try:
                enfant = utilisateur.admin
                self.fields['date_nomination'].initial = enfant.date_nomination
            except Admin.DoesNotExist:
                pass

        elif utilisateur.role == 'apiculteur':
            try:
                enfant = utilisateur.apiculteur
                self.fields['specialite'].initial = enfant.specialite
            except Apiculteur.DoesNotExist:
                pass

        elif utilisateur.role == 'responsable':
            try:
                enfant = utilisateur.responsable
                self.fields['niveau_experience'].initial = enfant.niveau_experience
            except Responsable.DoesNotExist:
                pass


class PremiereConnexionForm(SetPasswordForm):
    face_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )


class BeeFlowAuthenticationForm(AuthenticationForm):

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.statut == 'inactif':
            raise ValidationError(
                "Votre compte est désactivé. Contactez l'administrateur."
            )

        if user.statut == 'suspendu':
            raise ValidationError(
                "Votre compte est suspendu. Contactez l'administrateur."
            )


class ModifierMonCompteForm(forms.ModelForm):
    sexe = forms.ChoiceField(
        choices=[("", "Sélectionnez le sexe"), ("homme", "Homme"), ("femme", "Femme")],
        required=True,
        label="Sexe",
        error_messages={'required': "Veuillez sélectionner le sexe."}
    )

    date_naissance = forms.DateField(
        required=True,
        label="Date de naissance",
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date'}
        ),
        error_messages={'required': "La date de naissance est obligatoire."}
    )

    telephone = forms.CharField(
        required=True,
        label="Numéro de téléphone",
        max_length=13,
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': 'Numéro de téléphone'}),
        error_messages={'required': "Le numéro de téléphone est obligatoire."}
    )

    old_password = forms.CharField(
        label="Mot de passe actuel",
        required=True,
        widget=forms.PasswordInput()
    )

    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        required=False,
        widget=forms.PasswordInput()
    )

    new_password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        required=False,
        widget=forms.PasswordInput()
    )

    class Meta:
        model = Utilisateur
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'sexe',
            'date_naissance',
            'telephone',
        ]

    def clean_sexe(self):
        sexe = self.cleaned_data.get('sexe')
        if not sexe:
            raise forms.ValidationError("Veuillez sélectionner le sexe.")
        if sexe not in ['homme', 'femme']:
            raise forms.ValidationError("Le sexe sélectionné est invalide.")
        return sexe

    def clean_date_naissance(self):
        date = self.cleaned_data.get('date_naissance')
        if not date:
            raise forms.ValidationError("La date de naissance est obligatoire.")
        today = timezone.localdate()
        if date > today:
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        age = today.year - date.year - ((today.month, today.day) < (date.month, date.day))
        if age < 10:
            raise forms.ValidationError("L'utilisateur doit avoir au moins 10 ans.")
        if age > 120:
            raise forms.ValidationError("Veuillez entrer une date de naissance réaliste.")
        return date

    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone:
            raise forms.ValidationError("Le numéro de téléphone est obligatoire.")
        telephone = telephone.replace(" ", "").strip()
        if not re.match(r'^\+?[0-9]{8,12}$', telephone):
            raise forms.ValidationError("Veuillez saisir un numéro de téléphone valide (8 à 12 chiffres, ex: +21612345678 ou 12345678).")
        qs = Utilisateur.objects.filter(telephone=telephone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà associé à un autre compte.")
        return telephone

    def clean(self):
        cleaned_data = super().clean()

        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        # Vérifier l'ancien mot de passe
        if old_password and not self.instance.check_password(old_password):
            self.add_error(
                'old_password',
                "Votre mot de passe actuel est incorrect."
            )

        # Vérifier la confirmation du nouveau mot de passe
        if new_password1 or new_password2:

            if not new_password1:
                self.add_error(
                    'new_password1',
                    "Veuillez saisir le nouveau mot de passe."
                )

            if not new_password2:
                self.add_error(
                    'new_password2',
                    "Veuillez confirmer le nouveau mot de passe."
                )

            if new_password1 and new_password2 and new_password1 != new_password2:
                self.add_error(
                    'new_password2',
                    "Les deux mots de passe ne correspondent pas."
                )

            if new_password1 and new_password1 == new_password2:
                try:
                    validate_password(new_password1, self.instance)
                except ValidationError as error:
                    self.add_error('new_password1', error)

        return cleaned_data

    def save(self, commit=True):
        utilisateur = super().save(commit=False)

        nouveau_mot_de_passe = self.cleaned_data.get('new_password1')

        if nouveau_mot_de_passe:
            utilisateur.set_password(nouveau_mot_de_passe)

        if commit:
            utilisateur.save()

        return utilisateur
