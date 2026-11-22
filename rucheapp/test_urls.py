from django.http import HttpResponse
from django.urls import include, path


def page_vide(request):
    return HttpResponse("OK")


suivi_sanitaire_patterns = (
    [path("", page_vide, name="liste")],
    "suivi_sanitaire_bo",
)


urlpatterns = [
    path("", page_vide, name="accueil"),
    path("espace/", page_vide, name="espace"),
    path("dashboard/", page_vide, name="dashboard"),
    path(
        "dashboard/suivis/",
        include(suivi_sanitaire_patterns, namespace="suivi_sanitaire_bo"),
    ),
    path("dashboard/ruches/", include(("rucheapp.urls", "ruches"), namespace="ruches")),
    path("ruches/", include(("rucheapp.urls_frontoffice", "ruches_front"), namespace="ruches_front")),
]
