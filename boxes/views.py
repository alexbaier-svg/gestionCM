import datetime
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BoxForm
from .models import AsignacionBox, Box

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _clave_orden(box):
    m = re.search(r"\d+", box.nombre)
    return (0, int(m.group())) if m else (1, box.nombre)


class BoxListView(PermissionRequiredMixin, ListView):
    model = Box
    permission_required = "boxes.view_box"
    template_name = "boxes/lista.html"
    context_object_name = "boxes"

    def get_queryset(self):
        return Box.objects.all()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        boxes = sorted(contexto["boxes"], key=_clave_orden)
        contexto["boxes_piso1"] = [b for b in boxes if b.piso == 1]
        contexto["boxes_piso2"] = [b for b in boxes if b.piso == 2]
        return contexto


class BoxCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Box
    form_class = BoxForm
    permission_required = "boxes.add_box"
    template_name = "boxes/formulario.html"
    success_url = reverse_lazy("boxes:listar")
    success_message = "Box creado correctamente."


class BoxUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Box
    form_class = BoxForm
    permission_required = "boxes.change_box"
    template_name = "boxes/formulario.html"
    success_url = reverse_lazy("boxes:listar")
    success_message = "Box actualizado correctamente."


class BoxDeleteView(PermissionRequiredMixin, DeleteView):
    model = Box
    permission_required = "boxes.delete_box"
    template_name = "boxes/confirmar_eliminar.html"
    success_url = reverse_lazy("boxes:listar")

    def form_valid(self, form):
        messages.success(self.request, "Box eliminado.")
        return super().form_valid(form)


@login_required
def distribucion(request):
    try:
        dia = int(request.GET.get("dia"))
        if not 0 <= dia <= 6:
            raise ValueError
    except (TypeError, ValueError):
        dia = datetime.date.today().weekday()

    boxes = sorted(Box.objects.filter(activo=True), key=_clave_orden)
    asignaciones = AsignacionBox.objects.select_related("medico", "box")
    por_box = {}
    for a in asignaciones:
        por_box.setdefault(a.box_id, []).append(a)

    def _medicos_ese_dia(box):
        reglas = por_box.get(box.id, [])
        especificas = [a.medico.nombre_completo for a in reglas if a.dia_semana == dia]
        if especificas:
            return especificas
        return [a.medico.nombre_completo for a in reglas if a.dia_semana is None]

    def _preparar(lista_boxes):
        return [{"box": box, "medicos": _medicos_ese_dia(box)} for box in lista_boxes]

    contexto = {
        "dia": dia,
        "dias_tab": list(enumerate(DIAS_SEMANA)),
        "piso1": _preparar([b for b in boxes if b.piso == 1]),
        "piso2": _preparar([b for b in boxes if b.piso == 2]),
    }
    return render(request, "boxes/distribucion.html", contexto)
