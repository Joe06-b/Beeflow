
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (Utilisateur,Admin as AdminModel,Apiculteur,Responsable)
from .forms import UtilisateurCreationForm,UtilisateurChangeForm
from django.db import transaction


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    form = UtilisateurChangeForm
    add_form = UtilisateurCreationForm
    list_display = ('username','email','role','statut','telephone','created_at')
    list_filter = ('role', 'statut', 'sexe')
    search_fields = ('username',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'first_name',
                'last_name',
                'email',
            )
        }),
        ('Informations personnelles', {
            'fields': (
                'role',
                'sexe',
                'date_naissance',
                'telephone',
                'statut'
            )
        }),
        ('Informations spécifiques', {
            'fields': (
                'date_nomination',
                'specialite',
                'niveau_experience'
            )
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets

        return (
            ('Informations personnelles', {
                'fields': (
                'username',
                'first_name',
                'last_name',
                'email',
                'role',
                'sexe',
                'date_naissance',
                'telephone',
                'statut',
            )
            }),
            ('Informations spécifiques', {
                'fields': (
                    'date_nomination',
                    'specialite',
                    'niveau_experience',
                )
            }),
        )
    def creer_enfant(self, modele, obj):
        enfant = modele(utilisateur_ptr=obj)
        # Copier les champs du parent dans l'enfant
        for champ in Utilisateur._meta.concrete_fields:
            if not champ.primary_key:
                setattr(
                    enfant,
                    champ.attname,
                    getattr(obj, champ.attname)
                )
        return enfant
    
    @transaction.atomic
    def save_model(self, request, obj, form, change):
        # Sauvegarder d'abord l'utilisateur parent
        super().save_model(request, obj, form, change)
        data = form.cleaned_data

        if obj.role == 'admin':
            try:
                enfant = obj.admin
            except AdminModel.DoesNotExist:
                enfant = self.creer_enfant(AdminModel, obj)

            enfant.date_nomination = data.get('date_nomination')
            enfant.save()

        elif obj.role == 'apiculteur':
            try:
                enfant = obj.apiculteur
            except Apiculteur.DoesNotExist:
                enfant = self.creer_enfant(Apiculteur, obj)

            enfant.specialite = data.get('specialite')
            enfant.save()

        elif obj.role == 'responsable':
            try:
                enfant = obj.responsable
            except Responsable.DoesNotExist:
                enfant = self.creer_enfant(Responsable, obj)

            enfant.niveau_experience = data.get('niveau_experience')
            enfant.save()

