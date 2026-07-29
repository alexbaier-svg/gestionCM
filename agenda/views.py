import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Max, Min
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import ImportarAgendaForm
from .importador import decodificar_bytes, importar_agenda_csv
from .models import BloqueAgenda, ImportacionAgenda


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


def _resumen_por_medico(bloques_qs):
    return (
        bloques_qs
        .values("medico__nombre_completo", "box__nombre")
        .annotate(hora_min=Min("hora_inicio"), hora_max=Max("hora_fin"), cantidad=Count("id"))
        .order_by("medico__nombre_completo")
    )


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
        "resumen": _resumen_por_medico(bloques),
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

    ws_resumen = wb.create_sheet("Resumen por médico")
    encabezados_resumen = ["Médico", "Box", "Hora mín. desde", "Hora máx. hasta", "Cantidad de citas"]
    ws_resumen.append(encabezados_resumen)
    for fila in _resumen_por_medico(bloques):
        ws_resumen.append([
            fila["medico__nombre_completo"],
            fila["box__nombre"] or "Sin asignar",
            fila["hora_min"].strftime("%H:%M"),
            fila["hora_max"].strftime("%H:%M"),
            fila["cantidad"],
        ])
    for i, encabezado in enumerate(encabezados_resumen, start=1):
        ws_resumen.column_dimensions[get_column_letter(i)].width = max(16, len(encabezado) + 4)

    respuesta = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    respuesta["Content-Disposition"] = f'attachment; filename="agenda_{fecha.isoformat()}.xlsx"'
    wb.save(respuesta)
    return respuesta


@login_required
@permission_required("agenda.add_bloqueagenda", raise_exception=True)
def importar(request):
    if request.method == "POST":
        form = ImportarAgendaForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES["archivo"]
            try:
                texto = decodificar_bytes(archivo.read())
            except UnicodeDecodeError:
                messages.error(
                    request,
                    "No se pudo leer el archivo. Debe ser el CSV exportado tal cual, sin "
                    "convertir su codificación.",
                )
                return render(request, "agenda/importar.html", {"form": form})

            importacion = importar_agenda_csv(texto, archivo.name, request.user)
            messages.success(
                request,
                f"Importación completa: {importacion.filas_procesadas} filas procesadas, "
                f"{importacion.filas_omitidas} omitidas (recursos/equipos sin médico "
                f"asociado, o citas ya importadas antes).",
            )
            primer_bloque = importacion.bloques.first()
            if primer_bloque:
                return redirect(f"/agenda/?fecha={primer_bloque.fecha.isoformat()}")
            return redirect("agenda:diaria")
    else:
        form = ImportarAgendaForm()

    importaciones_recientes = ImportacionAgenda.objects.order_by("-fecha_importacion")[:10]
    return render(request, "agenda/importar.html", {
        "form": form,
        "importaciones_recientes": importaciones_recientes,
    })
