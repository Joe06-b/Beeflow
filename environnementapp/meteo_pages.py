"""Pages météo Frontoffice et Backoffice."""

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .meteo_permissions import meteo_admin_page_requis
from .models import Environnement


def _api_urls(namespace):
    return {
        "zones_url": reverse(f"{namespace}:api_zones_meteo"),
        "weather_url_template": reverse(
            f"{namespace}:api_meteo_zone",
            kwargs={"pk": 0},
        ).replace("/0/", "/__ZONE_ID__/"),
        "refresh_url_template": reverse(
            f"{namespace}:api_actualiser_meteo",
            kwargs={"pk": 0},
        ).replace("/0/", "/__ZONE_ID__/"),
    }


@meteo_admin_page_requis
def bo_meteo_liste(request):
    return render(
        request,
        "backoffice/environnementapp/meteo_liste.html",
        {
            "page_title": "Météo des zones",
            "active_page": "environnement",
            **_api_urls("environnement_bo"),
            "detail_url_template": reverse(
                "environnement_bo:meteo_detail",
                kwargs={"pk": 0},
            ).replace("/0/", "/__ZONE_ID__/"),
        },
    )


@meteo_admin_page_requis
def bo_meteo_detail(request, pk):
    zone = get_object_or_404(Environnement, pk=pk)
    return render(
        request,
        "backoffice/environnementapp/meteo_detail.html",
        {
            "page_title": f"Météo : {zone.nomZone}",
            "active_page": "environnement",
            "zone": zone,
            "weather_url": reverse(
                "environnement_bo:api_meteo_zone",
                kwargs={"pk": zone.pk},
            ),
            "meteo_scenarios_enabled": settings.DEBUG,
            "refresh_url": reverse(
                "environnement_bo:api_actualiser_meteo",
                kwargs={"pk": zone.pk},
            ),
        },
    )


def fo_meteo(request):
    return render(
        request,
        "frontoffice/environnementapp/meteo.html",
        {
            **_api_urls("environnement"),
            "meteo_scenarios_enabled": settings.DEBUG,
        },
    )
