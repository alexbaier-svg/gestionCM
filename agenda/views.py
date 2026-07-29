import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from .models import BloqueAgenda


def _bloques_del_dia(request, fecha):
    qs = (
        BloqueAgenda.objects.filter(fecha=fecha)
        .select_related("medico", "box")
        .exclude(estado=BloqueAgenda.Estado.ANULADO)
        .order_by("hora_inicio", "medico__nombre_completo")
    )
    medico_propio = getattr(request.user, "medico", None)
    es_gestion = request.user.groups.filter(name__in=["Administrador", "Recepción"]).exists()
    if medico_propio is not None and not request.user.is_superuser and not es_gestion:
        qs = qs.filter(medico=medico_propio)
    return qs


@login_required
def agenda_diaria(request):
    fecha_str = request.GET.get("fecha")
    try:
        fecha = datetime.date.fromisoformat(fecha_str) if fecha_str else datetime.date.today()
    except ValueError:
        fecha = datetime.date.today()

    bloques = _bloques_del_dia(request, fecha)
    contexto = {
        "fecha": fecha,
        "fecha_anterior": fecha - datetime.timedelta(days=1),
        "fecha_siguiente": fecha + datetime.timedelta(days=1),
        "bloques": bloques,
    }
    return render(request, "agenda/diaria.html", contexto)


@login_required
def agenda_diaria_excel(request):
    import openpyxl
    from openpyxl.utils import get_column_letter

    fecha_str = request.GET.get("fecha")
    try:
        fecha = datetime.date.fromisoformat(fecha_str) if fecha_str else datetime.date.today()
    except ValueError:
        fecha = datetime.date.today()

    bloques = _bloques_del_dia(request, fecha)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Agenda diaria"
    encabezados = ["Médico", "Especialidad", "Box", "Hora inicio", "Hora fin", "Estado"]
    ws.append(encabezados)
    for bloque in bloques:
        ws.append([
            bloque.medico.nombre_completo,
            bloque.especialidad,
            bloque.box.nombre if bloque.box else "Sin asignar",
            bloque.hora_inicio.strftime("%H:%M"),
            bloque.hora_fin.strftime("%H:%M"),
            bloque.get_estado_display(),
        ])
    for i, encabezado in enumerate(encabezados, start=1):
        ws.column_dimensions[get_column_letter(i)].width = max(14, len(encabezado) + 4)

    respuesta = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    respuesta["Content-Disposition"] = f'attachment; filename="agenda_{fecha.isoformat()}.xlsx"'
    wb.save(respuesta)
    return respuesta
