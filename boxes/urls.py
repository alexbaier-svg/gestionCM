from django.urls import path

from . import views

app_name = "boxes"

urlpatterns = [
    path("", views.BoxListView.as_view(), name="listar"),
    path("nuevo/", views.BoxCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.BoxUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.BoxDeleteView.as_view(), name="eliminar"),
    path("distribucion/", views.distribucion, name="distribucion"),
]
