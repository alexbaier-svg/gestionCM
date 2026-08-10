from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import UsuarioForm


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    accesos = []
    if request.user.has_perm("medicos.view_medico"):
        accesos.append({
            "titulo": "Médicos",
            "descripcion": "Ver, agregar y editar médicos.",
            "url": "medicos:listar",
            "icono": "🩺",
        })
    if request.user.has_perm("boxes.view_box"):
        accesos.append({
            "titulo": "Boxes",
            "descripcion": "Ver, agregar y editar boxes por piso.",
            "url": "boxes:listar",
            "icono": "🚪",
        })
    accesos.append({
        "titulo": "Distribución",
        "descripcion": "Ver qué médico tiene cada box, por piso.",
        "url": "boxes:distribucion",
        "icono": "🗺️",
    })
    accesos.append({
        "titulo": "Agenda diaria",
        "descripcion": "Ver y exportar la agenda de un día.",
        "url": "agenda:diaria",
        "icono": "📅",
    })
    accesos.append({
        "titulo": "Ocupación de boxes",
        "descripcion": "Mapa de calor: horas ocupadas según oferta y bloqueos.",
        "url": "disponibilidad:mapa_calor",
        "icono": "🔥",
    })
    accesos.append({
        "titulo": "Oferta",
        "descripcion": "Cuántas citas caben por médico y día de la semana.",
        "url": "disponibilidad:oferta_por_medico",
        "icono": "📈",
    })
    if (
        request.user.has_perm("agenda.add_bloqueagenda")
        or request.user.has_perm("disponibilidad.add_ofertamedico")
        or request.user.has_perm("disponibilidad.add_bloqueomedico")
    ):
        accesos.append({
            "titulo": "Importaciones",
            "descripcion": "Subir agenda, oferta o bloqueos desde el otro sistema.",
            "url": "importaciones",
            "icono": "⬆️",
        })
    if request.user.is_superuser or request.user.groups.filter(name="Administrador").exists():
        accesos.append({
            "titulo": "Reunión semanal",
            "descripcion": "Presentación de indicadores para la reunión semanal.",
            "url": "presentacion:listar_reuniones",
            "icono": "📊",
        })
    if request.user.has_perm("auth.view_user"):
        accesos.append({
            "titulo": "Usuarios",
            "descripcion": "Crear cuentas y asignar roles.",
            "url": "usuarios_listar",
            "icono": "👤",
        })
    return render(request, "core/dashboard.html", {"accesos": accesos})


@login_required
def importaciones(request):
    opciones = []
    if request.user.has_perm("agenda.add_bloqueagenda"):
        opciones.append({
            "titulo": "Agenda diaria",
            "descripcion": "Sube el archivo de citas del día (ExportarCitas).",
            "url": "agenda:importar",
            "icono": "📅",
        })
    if request.user.has_perm("disponibilidad.add_ofertamedico"):
        opciones.append({
            "titulo": "Oferta de médicos",
            "descripcion": "Sube el archivo de horarios de atención (ExportarOferta).",
            "url": "disponibilidad:importar_oferta",
            "icono": "🕒",
        })
    if request.user.has_perm("disponibilidad.add_bloqueomedico"):
        opciones.append({
            "titulo": "Bloqueos de médicos",
            "descripcion": "Sube el archivo de ausencias (ExportarBloqueos).",
            "url": "disponibilidad:importar_bloqueos",
            "icono": "🚫",
        })
    return render(request, "core/importaciones.html", {"opciones": opciones})


class UsuarioListView(PermissionRequiredMixin, ListView):
    model = User
    permission_required = "auth.view_user"
    template_name = "core/usuarios_lista.html"
    context_object_name = "usuarios"

    def get_queryset(self):
        return User.objects.all().order_by("username").prefetch_related("groups")


class UsuarioCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UsuarioForm
    permission_required = "auth.add_user"
    template_name = "core/usuario_formulario.html"
    success_url = reverse_lazy("usuarios_listar")
    success_message = "Usuario creado correctamente."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["es_nuevo"] = True
        return kwargs


class UsuarioUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UsuarioForm
    permission_required = "auth.change_user"
    template_name = "core/usuario_formulario.html"
    success_url = reverse_lazy("usuarios_listar")
    success_message = "Usuario actualizado correctamente."


class UsuarioDeleteView(PermissionRequiredMixin, DeleteView):
    model = User
    permission_required = "auth.delete_user"
    template_name = "core/usuario_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios_listar")

    def form_valid(self, form):
        messages.success(self.request, "Usuario eliminado.")
        return super().form_valid(form)
