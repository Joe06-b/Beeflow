from .meteo_permissions import meteo_admin_page_requis


def admin_requis(view_func):
    """Applique les permissions locales aux pages Backoffice Environnement."""
    return meteo_admin_page_requis(view_func)
