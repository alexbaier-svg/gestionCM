import datetime
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from boxes.models import AsignacionBox, Box
from boxes.views import _clave_orden
from medicos.models import Medico

from .calculos import minutos_brutos, minutos_libres
from .forms import ImportarBloqueosForm, ImportarOfertaForm
from .importador import importar_bloqueos_xlsx, importar_oferta_xlsx
from .models import BloqueoMedico, OfertaDiaria, OfertaMedico

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
@permission_required("disponibilidad.view_ofertamedico", raise_exception=True)
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
@permission_required("disponibilidad.view_ofertamedico", raise_exception=True)
def oferta_por_medico(request):
    q = request.GET.get("q", "").strip()
    medicos = Medico.objects.filter(activo=True)
    if q:
        medicos = medicos.filter(nombre_completo__icontains=q)
    medicos = medicos.order_by("nombre_completo")

    ofertas_por_medico = defaultdict(lambda: defaultdict(list))
    for o in OfertaMedico.objects.all():
        ofertas_por_medico[o.medico_id][o.dia_semana].append(o)

    bloqueos_por_medico = defaultdict(lambda: defaultdict(list))
    for b in BloqueoMedico.objects.all():
        bloqueos_por_medico[b.medico_id][b.dia_semana].append(b)

    filas = []
    for medico in medicos:
        duracion = medico.duracion_consulta_min or 15
        celdas = []
        for dia in range(7):
            ofertas = ofertas_por_medico[medico.id].get(dia, [])
            bloqueos = bloqueos_por_medico[medico.id].get(dia, [])
            brutos = minutos_brutos(ofertas)
            libres = minutos_libres(ofertas, bloqueos)
            celdas.append({
                "oferta": brutos // duracion,
                "bloqueos": (brutos - libres) // duracion,
            })
        filas.append({"medico": medico, "celdas": celdas})

    contexto = {
        "filas": filas,
        "dias_semana": DIAS_SEMANA,
        "q": q,
    }
    return render(request, "disponibilidad/oferta_por_medico.html", contexto)


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


@login_required
@permission_required("disponibilidad.view_ofertamedico", raise_exception=True)
def oferta_mensual(request):
    meses = sorted(
        {(f.year, f.month) for f in OfertaDiaria.objects.dates("fecha", "month")}, reverse=True
    )
    hoy = datetime.date.today()
    elegido = (hoy.year, hoy.month)
    try:
        anio, mes = (int(x) for x in request.GET.get("mes", "").split("-"))
        if (anio, mes) in meses:
            elegido = (anio, mes)
    except ValueError:
        pass
    if elegido not in meses and meses:
        elegido = meses[0]

    q = request.GET.get("q", "").strip()
    filas, totales, dias_cargados = [], {"oferta": 0, "bloqueos": 0, "efectiva": 0}, 0
    if meses:
        diarias = OfertaDiaria.objects.filter(fecha__year=elegido[0], fecha__month=elegido[1])
        dias_cargados = diarias.values("fecha").distinct().count()
        por_medico = defaultdict(lambda: [0, 0])
        for medico_id, oferta, bloqueos in diarias.values_list("medico_id", "oferta", "bloqueos"):
            por_medico[medico_id][0] += oferta
            por_medico[medico_id][1] += bloqueos
        medicos = Medico.objects.filter(activo=True).prefetch_related("especialidades")
        if q:
            medicos = medicos.filter(nombre_completo__icontains=q)
        for medico in medicos.order_by("nombre_completo"):
            oferta, bloqueos = por_medico.get(medico.id, [0, 0])
            totales["oferta"] += oferta
            totales["bloqueos"] += bloqueos
            totales["efectiva"] += oferta - bloqueos
            filas.append({
                "medico": medico,
                "especialidad": ", ".join(e.nombre for e in medico.especialidades.all()),
                "oferta": oferta,
                "bloqueos": bloqueos,
                "efectiva": oferta - bloqueos,
            })

    contexto = {
        "meses": [{"valor": f"{a}-{m:02d}", "texto": f"{MESES[m - 1].capitalize()} {a}"} for a, m in meses],
        "mes_elegido": f"{elegido[0]}-{elegido[1]:02d}",
        "filas": filas,
        "totales": totales,
        "dias_cargados": dias_cargados,
        "q": q,
    }
    return render(request, "disponibilidad/oferta_mensual.html", contexto)


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
            hoy = datetime.date.today()
            creados, omitidos = importar_bloqueos_xlsx(
                request.FILES["archivo"].read(),
                fecha_referencia=hoy,
                fecha_hasta_referencia=hoy + datetime.timedelta(days=6),
            )
            messages.success(
                request,
                f"Bloqueos importados: {creados} franjas cargadas, {omitidos} filas omitidas "
                f"(recursos sin médico asociado).",
            )
            return redirect("disponibilidad:alertas")
    else:
        form = ImportarBloqueosForm()
    return render(request, "disponibilidad/importar_bloqueos.html", {"form": form})
