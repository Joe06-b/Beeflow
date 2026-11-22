from functools import wraps


def admin_requis(view_func):
    """
    Protège les vues du back office.

    TEMPORAIRE : la gestion des utilisateurs est développée par un autre membre
    de l'équipe. En attendant, ce décorateur laisse passer tout le monde
    ("admin statique").

    INTÉGRATION : remplacer le corps de wrapper par la vérification de l'équipe, par ex. :

        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_staff:          # ou le rôle "admin" défini par mon ami
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    Toutes les vues du back office utilisent déjà @admin_requis :
    il n'y aura qu'un seul endroit à modifier.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return wrapper