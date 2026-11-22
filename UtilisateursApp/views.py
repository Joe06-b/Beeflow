import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Utilisateur, Admin, Apiculteur, Responsable
from .forms import UtilisateurCreationForm, UtilisateurChangeForm, PremiereConnexionForm,BeeFlowAuthenticationForm,ModifierMonCompteForm
from .face_utils import process_and_encode_face, authenticate_face
from django.views.decorators.http import require_POST
from django.contrib.auth.views import LoginView as DjangoLoginView
from .mixins import AdminRequisMixin
from django.contrib.auth.mixins import LoginRequiredMixin



# Synchroniser l'utilisateur avec sa classe fille selon son rôle
def synchroniser_role(utilisateur, data):

    configuration = {
        'admin': (Admin, 'admin', 'date_nomination'),
        'apiculteur': (Apiculteur, 'apiculteur', 'specialite'),
        'responsable': (Responsable, 'responsable', 'niveau_experience')
    }

    modele_cible, relation_cible, champ_specifique = configuration[utilisateur.role]
    enfant_cible = None

    # Récupérer la classe fille existante et supprimer les anciennes
    for modele, relation, champ in configuration.values():
        try:
            enfant = getattr(utilisateur, relation)
        except modele.DoesNotExist:
            continue

        if modele == modele_cible:
            enfant_cible = enfant
        else:
            enfant.delete(keep_parents=True)

    # Créer la classe fille si elle n'existe pas
    if enfant_cible is None:
        enfant_cible = modele_cible(utilisateur_ptr=utilisateur)

    # Copier les champs hérités depuis Utilisateur
    for champ in Utilisateur._meta.concrete_fields:
        if not champ.primary_key:
            setattr(
                enfant_cible,
                champ.attname,
                getattr(utilisateur, champ.attname)
            )

    # Affecter le champ spécifique au rôle
    setattr(enfant_cible, champ_specifique, data.get(champ_specifique))

    enfant_cible.save()


# 1. Liste des utilisateurs
class UtilisateurListView(ListView):
    model = Utilisateur
    template_name = 'backoffice/Utilisateurs/utilisateur_list.html'
    context_object_name = 'utilisateurs'
    ordering = ['-created_at']
    paginate_by = 10
    extra_context = {'active_page': 'utilisateurs', 'page_title': 'Gestion des utilisateurs'}

    def get_queryset(self):
        queryset = super().get_queryset()

        username = self.request.GET.get('username', '').strip()
        role = self.request.GET.get('role', '').strip()
        sexe = self.request.GET.get('sexe', '').strip()
        statut = self.request.GET.get('statut', '').strip()
        tri = self.request.GET.get('tri', '').strip()
        tri_statut = self.request.GET.get('tri_statut', '').strip()

        if username:
            queryset = queryset.filter(
                Q(username__icontains=username) |
                Q(first_name__icontains=username) |
                Q(last_name__icontains=username) |
                Q(email__icontains=username)
            )

        if role:
            queryset = queryset.filter(role=role)

        if sexe:
            queryset = queryset.filter(sexe=sexe)

        if statut:
            queryset = queryset.filter(statut=statut)

        if tri == 'statut_asc' or tri_statut == 'asc':
            queryset = queryset.order_by('statut')
        elif tri == 'statut_desc' or tri_statut == 'desc':
            queryset = queryset.order_by('-statut')
        elif tri == 'nom_asc':
            queryset = queryset.order_by('first_name', 'last_name', 'username')
        elif tri == 'nom_desc':
            queryset = queryset.order_by('-first_name', '-last_name', '-username')
        elif tri == 'ancien':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        context['params'] = params.urlencode()
        context['filtres_actifs'] = bool(
            self.request.GET.get('username') or
            self.request.GET.get('role') or
            self.request.GET.get('sexe') or
            self.request.GET.get('statut') or
            self.request.GET.get('tri') or
            self.request.GET.get('tri_statut')
        )
        return context


# Export CSV des utilisateurs (respecte les filtres actifs)
def utilisateur_export_csv(request):
    username = request.GET.get('username', '').strip()
    role = request.GET.get('role', '').strip()
    sexe = request.GET.get('sexe', '').strip()
    statut = request.GET.get('statut', '').strip()
    tri = request.GET.get('tri', '').strip()
    tri_statut = request.GET.get('tri_statut', '').strip()

    queryset = Utilisateur.objects.all()

    if username:
        queryset = queryset.filter(
            Q(username__icontains=username) |
            Q(first_name__icontains=username) |
            Q(last_name__icontains=username) |
            Q(email__icontains=username)
        )

    if role:
        queryset = queryset.filter(role=role)

    if sexe:
        queryset = queryset.filter(sexe=sexe)

    if statut:
        queryset = queryset.filter(statut=statut)

    if tri == 'statut_asc' or tri_statut == 'asc':
        queryset = queryset.order_by('statut')
    elif tri == 'statut_desc' or tri_statut == 'desc':
        queryset = queryset.order_by('-statut')
    elif tri == 'nom_asc':
        queryset = queryset.order_by('first_name', 'last_name', 'username')
    elif tri == 'nom_desc':
        queryset = queryset.order_by('-first_name', '-last_name', '-username')
    elif tri == 'ancien':
        queryset = queryset.order_by('created_at')
    else:
        queryset = queryset.order_by('-created_at')

    nom = f"utilisateurs_{timezone.localdate():%Y%m%d}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{nom}"'
    response.write("\ufeff")  # BOM pour accents corrects dans Excel

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "ID",
        "Nom d'utilisateur",
        "Prénom",
        "Nom",
        "Email",
        "Téléphone",
        "Sexe",
        "Date de naissance",
        "Rôle",
        "Statut",
        "Info spécifique rôle",
        "Date de création"
    ])

    for u in queryset:
        info_role = ""
        if u.role == 'admin':
            try:
                date_nom = u.admin.date_nomination
                info_role = f"Nomination: {date_nom.strftime('%d/%m/%Y')}" if date_nom else ""
            except Exception:
                pass
        elif u.role == 'apiculteur':
            try:
                info_role = f"Spécialité: {u.apiculteur.specialite or ''}"
            except Exception:
                pass
        elif u.role == 'responsable':
            try:
                info_role = f"Expérience: {u.responsable.get_niveau_experience_display() if u.responsable.niveau_experience else ''}"
            except Exception:
                pass

        date_creation = timezone.localtime(u.created_at).strftime('%d/%m/%Y') if u.created_at else ""
        date_naissance = u.date_naissance.strftime('%d/%m/%Y') if u.date_naissance else ""

        writer.writerow([
            u.id,
            u.username,
            u.first_name,
            u.last_name,
            u.email,
            u.telephone or "",
            u.get_sexe_display() if hasattr(u, 'get_sexe_display') and u.sexe else (u.sexe or ""),
            date_naissance,
            u.get_role_display() if hasattr(u, 'get_role_display') else u.role,
            u.get_statut_display() if hasattr(u, 'get_statut_display') else u.statut,
            info_role,
            date_creation
        ])

    return response


# 2. Statistiques des utilisateurs
class UtilisateurStatistiquesView(TemplateView):
    template_name = 'backoffice/Utilisateurs/statistiques.html'
    extra_context = {'active_page': 'utilisateurs', 'page_title': 'Statistiques des utilisateurs'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        total = Utilisateur.objects.count()
        nb_actifs = Utilisateur.objects.filter(statut='actif').count()
        nb_inactifs = Utilisateur.objects.filter(statut='inactif').count()
        nb_suspendus = Utilisateur.objects.filter(statut='suspendu').count()

        nb_apiculteurs = Utilisateur.objects.filter(role='apiculteur').count()
        nb_admins = Utilisateur.objects.filter(role='admin').count()
        nb_responsables = Utilisateur.objects.filter(role='responsable').count()

        nb_hommes = Utilisateur.objects.filter(sexe='homme').count()
        nb_femmes = Utilisateur.objects.filter(sexe='femme').count()
        nb_non_specifie = max(0, total - (nb_hommes + nb_femmes))

        il_y_a_30j = now - timedelta(days=30)
        nouveaux_30j = Utilisateur.objects.filter(created_at__gte=il_y_a_30j).count()

        taux_actifs = round((nb_actifs / total * 100), 1) if total > 0 else 0
        taux_apiculteurs = round((nb_apiculteurs / total * 100), 1) if total > 0 else 0

        # Évolution mensuelle sur les 6 derniers mois
        evolution_labels = []
        evolution_data = []
        mois_fr = ["", "Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
        for i in range(5, -1, -1):
            annee = now.year
            mois = now.month - i
            while mois <= 0:
                mois += 12
                annee -= 1
            debut_mois = timezone.datetime(annee, mois, 1, tzinfo=timezone.get_current_timezone())
            if mois == 12:
                fin_mois = timezone.datetime(annee + 1, 1, 1, tzinfo=timezone.get_current_timezone())
            else:
                fin_mois = timezone.datetime(annee, mois + 1, 1, tzinfo=timezone.get_current_timezone())

            nb = Utilisateur.objects.filter(created_at__gte=debut_mois, created_at__lt=fin_mois).count()
            evolution_labels.append(f"{mois_fr[mois]} {annee}")
            evolution_data.append(nb)

        # Spécialités d'apiculteurs
        specialites_qs = Apiculteur.objects.exclude(specialite__isnull=True).exclude(specialite='').values('specialite').annotate(nb=Count('id')).order_by('-nb')[:5]
        top_specialites = [{'nom': s['specialite'], 'nb': s['nb']} for s in specialites_qs]

        # Niveaux d'expérience des responsables
        exp_dict = {'debutant': 0, 'intermediaire': 0, 'experimente': 0}
        for r in Responsable.objects.all():
            if r.niveau_experience in exp_dict:
                exp_dict[r.niveau_experience] += 1
        niveaux_exp = [
            {'nom': 'Débutant', 'nb': exp_dict['debutant']},
            {'nom': 'Intermédiaire', 'nb': exp_dict['intermediaire']},
            {'nom': 'Expérimenté', 'nb': exp_dict['experimente']},
        ]

        derniers = Utilisateur.objects.order_by('-created_at')[:6]

        stats = {
            'total': total,
            'nb_actifs': nb_actifs,
            'taux_actifs': taux_actifs,
            'nb_inactifs': nb_inactifs,
            'nb_suspendus': nb_suspendus,
            'nb_apiculteurs': nb_apiculteurs,
            'taux_apiculteurs': taux_apiculteurs,
            'nb_admins': nb_admins,
            'nb_responsables': nb_responsables,
            'nb_hommes': nb_hommes,
            'nb_femmes': nb_femmes,
            'nb_non_specifie': nb_non_specifie,
            'nouveaux_30j': nouveaux_30j,
            'top_specialites': top_specialites,
            'niveaux_exp': niveaux_exp,
            'derniers': derniers,
        }

        graphiques = {
            'roles': {
                'labels': ['Apiculteurs', 'Responsables', 'Administrateurs'],
                'data': [nb_apiculteurs, nb_responsables, nb_admins],
            },
            'statuts': {
                'labels': ['Actifs', 'Inactifs', 'Suspendus'],
                'data': [nb_actifs, nb_inactifs, nb_suspendus],
            },
            'sexes': {
                'labels': ['Hommes', 'Femmes', 'Non spécifié'],
                'data': [nb_hommes, nb_femmes, nb_non_specifie],
            },
            'evolution': {
                'labels': evolution_labels,
                'data': evolution_data,
            }
        }

        context['stats'] = stats
        context['graphiques'] = graphiques
        context['onglet'] = 'stats'
        return context


# 3. Détails d'un utilisateur
class UtilisateurDetailView(DetailView):
    model = Utilisateur
    template_name = 'backoffice/Utilisateurs/utilisateur_detail.html'
    context_object_name = 'utilisateur'
    extra_context = {'active_page': 'utilisateurs', 'page_title': 'Détail utilisateur'}


# 3. Ajouter un utilisateur
class UtilisateurCreateView(CreateView):
    model = Utilisateur
    form_class = UtilisateurCreationForm
    template_name = 'backoffice/Utilisateurs/utilisateur_form.html'
    success_url = reverse_lazy('utilisateurs:liste')
    extra_context = {'active_page': 'utilisateurs', 'page_title': 'Ajouter un utilisateur'}

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        synchroniser_role(self.object, form.cleaned_data)
        if 'enregistrer_et_ajouter' in self.request.POST:
            return redirect('utilisateurs:ajouter')
        return HttpResponseRedirect(self.get_success_url())


# 4. Modifier un utilisateur
class UtilisateurUpdateView(UpdateView):
    model = Utilisateur
    form_class = UtilisateurChangeForm
    template_name = 'backoffice/Utilisateurs/utilisateur_form.html'
    context_object_name = 'utilisateur'
    success_url = reverse_lazy('utilisateurs:liste')
    extra_context = {'active_page': 'utilisateurs', 'page_title': 'Modifier un utilisateur'}

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        synchroniser_role(self.object, form.cleaned_data)
        return HttpResponseRedirect(self.get_success_url())


# 5. Supprimer un utilisateur
class UtilisateurDeleteView(AdminRequisMixin,DeleteView):
    model = Utilisateur
    template_name = 'backoffice/Utilisateurs/utilisateur_confirm_delete.html'
    context_object_name = 'utilisateur'
    success_url = reverse_lazy('utilisateurs:liste')
    extra_context = {'active_page': 'utilisateurs', 'page_title': 'Supprimer un utilisateur'}



@login_required
def dispatch_apres_connexion(request):
    user = request.user

    if user.premiere_connexion:
        return redirect('premiere_connexion')

    if user.role == 'admin':
        return redirect('dashboard')

    return redirect('espace')


@login_required
def premiere_connexion_view(request):
    user = request.user

    if not user.premiere_connexion:
        return redirect('dispatch_connexion')

    if request.method == 'POST':
        form = PremiereConnexionForm(user, request.POST)
        
        if form.is_valid():
            form.save()

            face_data = form.cleaned_data.get('face_data')

            if face_data:
                success, msg, payload = process_and_encode_face(face_data)

                if success:
                    user.face_encoding = payload
                    user.face_configured = True
                else:
                    messages.warning(request, msg)

            user.premiere_connexion = False
            user.save()

            messages.success(
                request,
                "Votre compte a été configuré avec succès."
            )

            return redirect('dispatch_connexion')

    else:
        form = PremiereConnexionForm(user)

    return render(
        request,
        'registration/premiere_connexion.html',
        {
            'form': form,
            'utilisateur': user,
            'page_title': 'Première connexion'
        }
    )


@require_POST
def login_face_api(request):
    try:
        data = json.loads(request.body)
        image_base64 = data.get('image', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'Données invalides.'
        }, status=400)

    if not image_base64:
        return JsonResponse({
            'success': False,
            'error': 'Aucune image reçue.'
        }, status=400)

    users_with_face = Utilisateur.objects.filter(
        statut='actif',
        is_active=True,
        face_configured=True,
        premiere_connexion=False
    )

    matched_user, score, message = authenticate_face(
        image_base64,
        users_with_face,
        threshold=0.72
    )

    if matched_user is None:
        return JsonResponse({
            'success': False,
            'error': message
        })

    auth_login(request, matched_user)

    redirect_url = (
        reverse('dashboard')
        if matched_user.role == 'admin'
        else reverse('espace')
    )

    return JsonResponse({
        'success': True,
        'username': matched_user.username,
        'role': matched_user.get_role_display(),
        'redirect_url': redirect_url
    })

class BeeFlowLoginView(DjangoLoginView):
    template_name = 'registration/login.html'
    authentication_form = BeeFlowAuthenticationForm
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dispatch_connexion')
        return super().dispatch(request, *args, **kwargs)
    def form_invalid(self, form):
        messages.error(
            self.request,
            "Nom d'utilisateur ou mot de passe incorrect."
        )
        return super().form_invalid(form)


class ModifierMonCompteView(LoginRequiredMixin, UpdateView):
    model = Utilisateur
    form_class = ModifierMonCompteForm
    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', '/')

    def form_valid(self, form):
        form.save()

        messages.success(self.request,"Votre compte a été modifié avec succès.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        for erreurs in form.errors.values():
            for erreur in erreurs:
                messages.error(self.request, erreur)
        return redirect(self.get_success_url())

class SupprimerMonCompteView(LoginRequiredMixin, DeleteView):
    model = Utilisateur
    def get_object(self, queryset=None):
        return self.request.user
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        mot_de_passe = request.POST.get('password')
        # Vérifier le mot de passe actuel
        if not mot_de_passe or not self.object.check_password(mot_de_passe):
            messages.error(request,"Le mot de passe saisi est incorrect.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Supprimer le compte
        auth_logout(request)
        self.object.delete()
        messages.success(request,"Votre compte a été supprimé avec succès.")
        return redirect('accueil')
