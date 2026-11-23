from django.views.generic import TemplateView
from UtilisateursApp.mixins import UtilisateurMetierRequisMixin,AdminRequisMixin


class EspaceView(TemplateView):
    template_name = 'frontoffice/espace.html'

class DashboardView(TemplateView):
    template_name = 'backoffice/dashboard.html'

    extra_context = {
        'page_title': 'Tableau de bord',
        'active_page': 'dashboard'
    }