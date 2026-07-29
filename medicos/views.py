from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from boxes.models import AsignacionBox, Box

from .forms import MedicoForm
from .models import Medico

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class MedicoListView(PermissionRequiredMixin, ListView):
    model = Medico
    permission_required = "medicos.view_medico"
    template_name = "medicos/lista.html"
    context_object_name = "medicos"
    paginate_by = 25

    def get_queryset(self):
        qs = Medico.objects.all().order_by("nombre_completo")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(nombre_completo__icontains=q)
        return qs


class MedicoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Medico
    form_class = MedicoForm
    permission_required = "medicos.add_medico"
    template_name = "medicos/formulario.html"
    success_url = reverse_lazy("medicos:listar")
    success_message = "Médico creado correctamente."


class MedicoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Medico
    form_class = MedicoForm
    permission_required = "medicos.change_medico"
    template_name = "medicos/formulario.html"
    success_url = reverse_lazy("medicos:listar")
    success_message = "Médico actualizado correctamente."


class MedicoDeleteView(PermissionRequiredMixin, DeleteView):
    model = Medico
    permission_required = "medicos.delete_medico"
    template_name = "medicos/confirmar_eliminar.html"
    success_url = reverse_lazy("medicos:listar")

    def form_valid(self, form):
        messages.success(self.request, "Médico eliminado.")
        return super().form_valid(form)


def boxes_del_medico(request, pk):
    if not request.user.has_perm("boxes.view_asignacionbox"):
        return redirect("dashboard")

    medico = get_object_or_404(Medico, pk=pk)

    if request.method == "POST" and request.user.has_perm("boxes.add_asignacionbox"):
        if "eliminar" in request.POST:
            AsignacionBox.objects.filter(pk=request.POST["eliminar"], medico=medico).delete()
            messages.success(request, "Asignación eliminada.")
        else:
            box_id = request.POST.get("box")
            dia = request.POST.get("dia_semana") or None
            if box_id:
                AsignacionBox.objects.get_or_create(medico=medico, box_id=box_id, dia_semana=dia)
                messages.success(request, "Box asignado.")
        return redirect("medicos:boxes", pk=medico.pk)

    contexto = {
        "medico": medico,
        "asignaciones": medico.asignaciones_box.select_related("box").order_by("box__nombre"),
        "boxes_disponibles": Box.objects.filter(activo=True).order_by("nombre"),
        "dias_semana": list(enumerate(DIAS_SEMANA)),
        "puede_editar": request.user.has_perm("boxes.add_asignacionbox"),
    }
    return render(request, "medicos/boxes_del_medico.html", contexto)
