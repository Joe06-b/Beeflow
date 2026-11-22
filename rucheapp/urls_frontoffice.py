from django.urls import path

from .views import (
    RucheFrontDetailView,
    RucheFrontListView,

)

app_name = "ruches_front"

urlpatterns = [
    path("", RucheFrontListView.as_view(), name="liste"),
    path("<int:pk>/", RucheFrontDetailView.as_view(), name="detail"),
]
