from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class AdminRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'admin'

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('espace')
        return super().handle_no_permission()


class ApiculteurRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'apiculteur'
    
    def handle_no_permission(self):
            if self.request.user.is_authenticated:
                return redirect('dashboard')
            return super().handle_no_permission()


class ResponsableRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'responsable'

    def handle_no_permission(self):
                if self.request.user.is_authenticated:
                    return redirect('dashboard')
                return super().handle_no_permission()

class UtilisateurMetierRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role in ['apiculteur', 'responsable']
    def handle_no_permission(self):
                if self.request.user.is_authenticated:
                    return redirect('dashboard')
                return super().handle_no_permission()
