"""Lógica compartida para importar una agenda diaria (CSV UTF-16 del sistema externo).

Usada tanto por el comando `manage.py importar_agenda` (carga por línea de comandos) como
por la vista web de importación. Ver CLAUDE.md para el detalle del formato del archivo y
las decisiones de diseño (descarte de PHI, matching por RUT, box automático).
"""

import csv
import io
import unicodedata
from datetime import datetime

from django.db import transaction

from boxes.models import AsignacionBox
from medicos.models import Medico

from .models import BloqueAgenda, ImportacionAgenda

ESTADO_MAP = {
    "citado": BloqueAgenda.Estado.CITADO,
    "confirmado": BloqueAgenda.Estado.CONFIRMADO,
    "anulado": BloqueAgenda.Estado.ANULADO,
    "bloqueado": BloqueAgenda.Estado.BLOQUEADO,
    "atendido": BloqueAgenda.Estado.ATENDIDO,
}

AREA_VALIDA = "consulta presencial"


def _norm(texto):
    return (texto or "").strip()


def _normalizar_comparable(texto):
    sin_acentos = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return sin_acentos.strip().lower()


def _valor_columna(fila, nombre_normalizado):
    """Busca una columna por nombre normalizado (sin tildes, minúscula), ya que la
    codificación del CSV puede variar cómo llegan las tildes en los encabezados."""
    for clave, valor in fila.items():
        if _normalizar_comparable(clave) == nombre_normalizado:
            return valor
    return None


def _resolver_box(medico, fecha):
    dia_semana = fecha.weekday()
    asignacion = (
        AsignacionBox.objects.filter(medico=medico, dia_semana=dia_semana).first()
        or AsignacionBox.objects.filter(medico=medico, dia_semana__isnull=True).first()
    )
    return asignacion.box if asignacion else None


def _procesar_fila(fila, importacion):
    area_valor = _valor_columna(fila, "area")
    if area_valor is not None and _normalizar_comparable(area_valor) != AREA_VALIDA:
        # Solo interesan las citas de consulta presencial (no imágenes,
        # procedimientos, etc.). Si la columna 'Área' no se pudo ubicar en el
        # archivo (variación de formato/codificación), no se filtra por área —
        # es preferible incluir de más que descartar todas las filas por error.
        return False

    rut = _norm(fila.get("No. Documento Profesional"))
    nombre_recurso = _norm(fila.get("Profesional/Recurso"))
    appointment_id = _norm(fila.get("AppointmentId")) or None

    medico = None
    if rut:
        medico = Medico.objects.filter(rut__iexact=rut).first()
    if medico is None and nombre_recurso:
        medico = Medico.objects.filter(nombre_completo__iexact=nombre_recurso).first()
    if medico is None:
        # Fila de recurso/equipo (ej. scanner, resonador) sin médico asociado: se omite.
        return False

    if appointment_id and BloqueAgenda.objects.filter(id_externo=appointment_id).exists():
        return False  # ya importado antes

    try:
        fecha = datetime.strptime(_norm(fila.get("Fecha desde")), "%d-%m-%Y").date()
        hora_inicio = datetime.strptime(_norm(fila.get("Hora desde")), "%H:%M").time()
        hora_fin = datetime.strptime(_norm(fila.get("Hora hasta")), "%H:%M").time()
    except ValueError:
        return False

    estado = ESTADO_MAP.get(_norm(fila.get("Estado")).lower(), BloqueAgenda.Estado.OTRO)
    box = _resolver_box(medico, fecha)

    BloqueAgenda.objects.create(
        medico=medico,
        box=box,
        especialidad=_norm(fila.get("Especialidad")),
        id_externo=appointment_id,
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        estado=estado,
        origen=BloqueAgenda.Origen.IMPORTADO,
        importacion=importacion,
    )
    return True


def decodificar_bytes(contenido):
    """Decodifica el contenido crudo del CSV subido (UTF-16, con o sin BOM)."""
    if contenido.startswith(b"\xff\xfe") or contenido.startswith(b"\xfe\xff"):
        texto = contenido.decode("utf-16")
    else:
        texto = contenido.decode("utf-16-le")
    return io.StringIO(texto)


def importar_agenda_csv(archivo_texto, nombre_archivo, usuario=None):
    """archivo_texto: iterable de líneas de texto ya decodificadas (ej. TextIOWrapper).

    Devuelve la instancia de ImportacionAgenda creada, con filas_procesadas/omitidas.
    """
    lector = csv.DictReader(archivo_texto)
    procesadas = 0
    omitidas = 0
    with transaction.atomic():
        importacion = ImportacionAgenda.objects.create(
            archivo_nombre=nombre_archivo, usuario=usuario
        )
        for fila in lector:
            if _procesar_fila(fila, importacion):
                procesadas += 1
            else:
                omitidas += 1
        importacion.filas_procesadas = procesadas
        importacion.filas_omitidas = omitidas
        importacion.save(update_fields=["filas_procesadas", "filas_omitidas"])
    return importacion
