from django.urls import path

from . import views

app_name = "presentacion"

urlpatterns = [
    path("", views.listar_reuniones, name="listar_reuniones"),
    path("<int:reunion_id>/", views.visor, name="visor"),
]
