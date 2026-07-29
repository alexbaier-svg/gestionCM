import datetime
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from boxes.models import AsignacionBox, Box
from boxes.views import _clave_orden

from .forms import ImportarBloqueosForm, ImportarOfertaForm
from .importador import importar_bloqueos_xlsx, importar_oferta_xlsx
from .models import BloqueoMedico, OfertaMedico

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
HORA_INICIO_CENTRO = datetime.time(8, 0)
HORA_FIN_CENTRO = datetime.time(20, 0)
PASO_MINUTOS = 30


def _slots():
    slots = []
    actual = datetime.datetime.combine(datetime.date.today(), HORA_INICIO_CENTRO)
    fin = datetime.datetime.combine(datetime.date.today(), HORA_FIN_CENTRO)
    while actual < fin:
        siguiente = actual + datetime.timedelta(minutes=PASO_MINUTOS)
        slots.append((actual.time(), siguiente.time()))
        actual = siguiente
    return slots


def _medicos_del_box_ese_dia(box, dia, por_box):
    reglas = por_box.get(box.id, [])
    especificas = [a.medico for a in reglas if a.dia_semana == dia]
    if especificas:
        return especificas
    return [a.medico for a in reglas if a.dia_semana is None]


@login_required
def mapa_calor(request):
    try:
        dia = int(request.GET.get("dia"))
        if not 0 <= dia <= 6:
            raise ValueError
    except (TypeError, ValueError):
        dia = datetime.date.today().weekday()

    piso = request.GET.get("piso", "todos")
    if piso not in ("1", "2", "todos"):
        piso = "todos"

    boxes = sorted(Box.objects.filter(activo=True), key=_clave_orden)
    if piso != "todos":
        boxes = [b for b in boxes if b.piso == int(piso)]

    por_box = defaultdict(list)
    for a in AsignacionBox.objects.select_related("medico", "box"):
        por_box[a.box_id].append(a)

    ofertas_por_medico = defaultdict(list)
    for o in OfertaMedico.objects.filter(dia_semana=dia):
        ofertas_por_medico[o.medico_id].append(o)

    bloqueos_por_medico = defaultdict(list)
    for b in BloqueoMedico.objects.filter(dia_semana=dia):
        bloqueos_por_medico[b.medico_id].append(b)

    def _disponible(medico, slot_inicio, slot_fin):
        cubierto = any(
            o.hora_inicio <= slot_inicio and slot_fin <= o.hora_fin
            for o in ofertas_por_medico.get(medico.id, [])
        )
        if not cubierto:
            return False
        for b in bloqueos_por_medico.get(medico.id, []):
            if b.tipo == BloqueoMedico.Tipo.DIA_COMPLETO:
                return False
            if b.hora_inicio <= slot_inicio < b.hora_fin:
                return False
        return True

    slots = _slots()
    filas = []
    for box in boxes:
        medicos = _medicos_del_box_ese_dia(box, dia, por_box)
        celdas = []
        for slot_inicio, slot_fin in slots:
            ocupantes = [m.nombre_completo for m in medicos if _disponible(m, slot_inicio, slot_fin)]
            celdas.append({"ocupado": bool(ocupantes), "medicos": ", ".join(ocupantes)})
        filas.append({"box": box, "celdas": celdas})

    contexto = {
        "dia": dia,
        "dias_tab": list(enumerate(DIAS_SEMANA)),
        "piso": piso,
        "slots": [s.strftime("%H:%M") for s, _ in slots],
        "filas": filas,
    }
    return render(request, "disponibilidad/mapa_calor.html", contexto)


@login_required
def alertas(request):
    pares_con_oferta = set(OfertaMedico.objects.values_list("medico_id", "dia_semana"))
    bloqueos_sin_oferta = [
        {
            "medico": b.medico.nombre_completo,
            "dia": DIAS_SEMANA[b.dia_semana],
            "hora_inicio": b.hora_inicio,
            "hora_fin": b.hora_fin,
            "tipo": b.get_tipo_display(),
            "motivo": b.motivo,
        }
        for b in BloqueoMedico.objects.select_related("medico").order_by(
            "medico__nombre_completo", "dia_semana"
        )
        if (b.medico_id, b.dia_semana) not in pares_con_oferta
    ]
    return render(request, "disponibilidad/alertas.html", {"bloqueos_sin_oferta": bloqueos_sin_oferta})


@login_required
@permission_required("disponibilidad.add_ofertamedico", raise_exception=True)
def importar_oferta(request):
    if request.method == "POST":
        form = ImportarOfertaForm(request.POST, request.FILES)
        if form.is_valid():
            creadas, omitidas = importar_oferta_xlsx(request.FILES["archivo"].read())
            messages.success(
                request,
                f"Oferta importada: {creadas} franjas cargadas, {omitidas} filas omitidas "
                f"(recursos sin médico asociado).",
            )
            return redirect("disponibilidad:mapa_calor")
    else:
        form = ImportarOfertaForm()
    return render(request, "disponibilidad/importar_oferta.html", {"form": form})


@login_required
@permission_required("disponibilidad.add_bloqueomedico", raise_exception=True)
def importar_bloqueos(request):
    if request.method == "POST":
        form = ImportarBloqueosForm(request.POST, request.FILES)
        if form.is_valid():
            creados, omitidos = importar_bloqueos_xlsx(request.FILES["archivo"].read())
            messages.success(
                request,
                f"Bloqueos importados: {creados} franjas cargadas, {omitidos} filas omitidas "
                f"(recursos sin médico asociado).",
            )
            return redirect("disponibilidad:alertas")
    else:
        form = ImportarBloqueosForm()
    return render(request, "disponibilidad/importar_bloqueos.html", {"form": form})
