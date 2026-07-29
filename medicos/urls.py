from django.urls import path

from . import views

app_name = "medicos"

urlpatterns = [
    path("", views.MedicoListView.as_view(), name="listar"),
    path("nuevo/", views.MedicoCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.MedicoUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.MedicoDeleteView.as_view(), name="eliminar"),
    path("<int:pk>/boxes/", views.boxes_del_medico, name="boxes"),
    path("especialidades/", views.EspecialidadListView.as_view(), name="especialidades"),
    path("especialidades/nueva/", views.EspecialidadCreateView.as_view(), name="especialidad_crear"),
    path("especialidades/<int:pk>/editar/", views.EspecialidadUpdateView.as_view(), name="especialidad_editar"),
    path("especialidades/<int:pk>/eliminar/", views.EspecialidadDeleteView.as_view(), name="especialidad_eliminar"),
]
