from django.urls import path

from . import views

app_name = "disponibilidad"

urlpatterns = [
    path("mapa-calor/", views.mapa_calor, name="mapa_calor"),
    path("alertas/", views.alertas, name="alertas"),
    path("importar-oferta/", views.importar_oferta, name="importar_oferta"),
    path("importar-bloqueos/", views.importar_bloqueos, name="importar_bloqueos"),
]
