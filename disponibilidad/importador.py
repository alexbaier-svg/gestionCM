"""Importa los archivos 'ExportarOferta' y 'ExportarBloqueos' del sistema externo.

Ninguno de los dos archivos trae RUT del profesional, pero sí un 'IDRecurso' numérico
estable (el identificador interno del recurso en el sistema externo). El matching con
Medico se hace en este orden:
  1. Por IDRecurso, si el médico ya tiene uno guardado de una importación anterior
     (rápido y a prueba de cambios de nombre).
  2. Por nombre exacto (normalizado: sin tildes, en mayúsculas, comparando el conjunto
     de palabras sin importar el orden) — ej. "Pablo Andres Giannini" vs.
     "GIANNINI PABLO ANDRES". Si calza, se guarda su IDRecurso para la próxima vez.
  3. Por subconjunto de palabras: si el nombre del archivo trae una palabra de más o de
     menos que el registrado (ej. le agregaron un segundo nombre) pero todas las demás
     coinciden, y esto resuelve a un único médico sin ambigüedad, también se acepta y se
     guarda su IDRecurso.
Filas cuyo recurso no resuelve por ninguna de las tres vías (equipos, salas, u otros
profesionales aún no cargados, o coincidencias ambiguas) se omiten sin adivinar.

Cada importación reemplaza por completo los datos anteriores: los archivos representan
el estado vigente de la oferta/bloqueos, no un historial acumulable.
"""

import datetime
import io
import unicodedata

import openpyxl
from django.db import transaction

from medicos.models import Medico

from .models import BloqueoMedico, OfertaMedico


def _normalizar_nombre(texto):
    texto = unicodedata.normalize("NFKD", texto.upper()).encode("ascii", "ignore").decode("ascii")
    return frozenset(t for t in texto.split() if t)


class _ResolvedorMedicos:
    """Resuelve el Medico de una fila (IDRecurso, NombreRecurso), con las tres vías
    descritas en el docstring del módulo. Guarda id_recurso_oferta la primera vez que
    lo aprende, para que las próximas importaciones no dependan del nombre."""

    def __init__(self):
        medicos = list(Medico.objects.all())
        self._por_id = {m.id_recurso_oferta: m for m in medicos if m.id_recurso_oferta is not None}
        self._por_nombre_exacto = {_normalizar_nombre(m.nombre_completo): m for m in medicos}
        self._candidatos_subconjunto = [(_normalizar_nombre(m.nombre_completo), m) for m in medicos]
        self._por_actualizar = {}

    def resolver(self, idrecurso, nombre):
        if idrecurso in self._por_id:
            return self._por_id[idrecurso]

        nombre = (nombre or "").strip()
        if not nombre:
            return None
        nombre_norm = _normalizar_nombre(nombre)

        medico = self._por_nombre_exacto.get(nombre_norm)
        if medico is None:
            candidatos = [
                m for palabras, m in self._candidatos_subconjunto
                if palabras and (palabras <= nombre_norm or nombre_norm <= palabras)
                and len(palabras & nombre_norm) >= 2
            ]
            if len(candidatos) == 1:
                medico = candidatos[0]

        if medico is not None and idrecurso is not None and medico.id_recurso_oferta != idrecurso:
            self._por_id[idrecurso] = medico
            self._por_actualizar[medico.pk] = idrecurso
        return medico

    def guardar_ids_aprendidos(self):
        if not self._por_actualizar:
            return
        medicos = Medico.objects.in_bulk(self._por_actualizar.keys())
        for pk, idrecurso in self._por_actualizar.items():
            medicos[pk].id_recurso_oferta = idrecurso
        Medico.objects.bulk_update(medicos.values(), ["id_recurso_oferta"])


def _parsear_hora(texto):
    horas, minutos = texto.split(":")
    return datetime.time(int(horas), int(minutos))


def _parsear_fecha_validez(texto):
    """'Validodesde'/'Validohasta' vienen como '9/21/2026 12:00:00 AM -03:00'."""
    return datetime.datetime.strptime(texto.split(" ")[0], "%m/%d/%Y").date()


def _cargar_libro(contenido_bytes):
    return openpyxl.load_workbook(io.BytesIO(contenido_bytes), data_only=True)


def _es_consulta(nombre_servicio):
    return _normalizar_comparable(nombre_servicio).startswith("consulta")


def _normalizar_comparable(texto):
    sin_acentos = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return sin_acentos.strip().lower()


def _ofertas_de_consulta(wb):
    """IDs de oferta (bloque horario) que corresponden a consultas médicas, según la
    hoja ServicioOferta. Excluye bloques exclusivos para imágenes/procedimientos/
    vacunas, que nunca aparecen como cita en la agenda diaria (filtrada por
    Área=Consulta Presencial) y no deben contarse como oferta de citas."""
    ws_servicios = wb["ServicioOferta"]
    con_servicio = {}
    for fila in ws_servicios.iter_rows(min_row=2, values_only=True):
        id_oferta, nombre_servicio = fila[0], fila[3]
        if not id_oferta or not nombre_servicio:
            continue
        con_servicio[id_oferta] = con_servicio.get(id_oferta, False) or _es_consulta(nombre_servicio)
    return con_servicio


def importar_oferta_xlsx(contenido_bytes, fecha_referencia=None):
    """fecha_referencia: solo se importan bloques cuyo rango Validodesde/Validohasta
    cubra esta fecha (el archivo trae, para un mismo médico, varias 'ofertas' con
    rangos de vigencia distintos — ej. una plantilla de horario vigente esta semana y
    otra ya programada para octubre — y sumarlas todas duplica su disponibilidad).
    Por defecto, hoy."""
    fecha_referencia = fecha_referencia or datetime.date.today()
    wb = _cargar_libro(contenido_bytes)
    ws_ofertas = wb["Ofertas"]
    ws_horarios = wb["HorariosOfertas"]
    resolvedor = _ResolvedorMedicos()
    ofertas_consulta = _ofertas_de_consulta(wb)

    medico_por_oferta = {}
    for fila in ws_ofertas.iter_rows(min_row=2, values_only=True):
        id_oferta, idrecurso, nombre_recurso = fila[1], fila[2], fila[3]
        desde, hasta = fila[6], fila[7]
        vigente = (
            desde and hasta
            and _parsear_fecha_validez(desde) <= fecha_referencia <= _parsear_fecha_validez(hasta)
        )
        medico_por_oferta[id_oferta] = resolvedor.resolver(idrecurso, nombre_recurso) if vigente else None

    creadas, omitidas = 0, 0
    nuevas = []
    for fila in ws_horarios.iter_rows(min_row=2, values_only=True):
        id_oferta = fila[0]
        hora_desde, hora_hasta = fila[2], fila[3]
        marcas_dias = fila[4:11]
        medico = medico_por_oferta.get(id_oferta)
        # Si el bloque no tiene servicios registrados, no se filtra por tipo (mejor
        # incluir de más que descartar de más por falta de dato).
        es_consulta = ofertas_consulta.get(id_oferta, True)
        if medico is None or not hora_desde or not hora_hasta or not es_consulta:
            omitidas += 1
            continue
        for indice_dia, marca in enumerate(marcas_dias):
            if marca:
                nuevas.append(OfertaMedico(
                    medico=medico,
                    dia_semana=indice_dia,
                    hora_inicio=_parsear_hora(hora_desde),
                    hora_fin=_parsear_hora(hora_hasta),
                ))
                creadas += 1

    with transaction.atomic():
        OfertaMedico.objects.all().delete()
        OfertaMedico.objects.bulk_create(nuevas)
        resolvedor.guardar_ids_aprendidos()

    return creadas, omitidas


def importar_bloqueos_xlsx(contenido_bytes, fecha_referencia=None):
    """Ver docstring de importar_oferta_xlsx: mismo filtro de vigencia por fecha."""
    fecha_referencia = fecha_referencia or datetime.date.today()
    wb = _cargar_libro(contenido_bytes)
    ws_bloqueos = wb["Bloqueos"]
    ws_horarios = wb["HorariosBloqueos"]
    resolvedor = _ResolvedorMedicos()

    info_por_bloqueo = {}
    for fila in ws_bloqueos.iter_rows(min_row=2, values_only=True):
        id_bloqueo, idrecurso, nombre_recurso = fila[0], fila[1], fila[2]
        desde, hasta = fila[5], fila[6]
        tipo, motivo = fila[9], fila[10]
        vigente = (
            desde and hasta
            and _parsear_fecha_validez(desde) <= fecha_referencia <= _parsear_fecha_validez(hasta)
        )
        info_por_bloqueo[id_bloqueo] = {
            "medico": resolvedor.resolver(idrecurso, nombre_recurso) if vigente else None,
            "tipo": tipo or BloqueoMedico.Tipo.PARCIAL,
            "motivo": (motivo or "").strip(),
        }

    creados, omitidos = 0, 0
    nuevos = []
    for fila in ws_horarios.iter_rows(min_row=2, values_only=True):
        id_bloqueo = fila[0]
        hora_desde, hora_hasta = fila[2], fila[3]
        marcas_dias = fila[4:11]
        info = info_por_bloqueo.get(id_bloqueo)
        medico = info["medico"] if info else None
        if medico is None or not hora_desde or not hora_hasta:
            omitidos += 1
            continue
        for indice_dia, marca in enumerate(marcas_dias):
            if marca:
                nuevos.append(BloqueoMedico(
                    medico=medico,
                    dia_semana=indice_dia,
                    hora_inicio=_parsear_hora(hora_desde),
                    hora_fin=_parsear_hora(hora_hasta),
                    tipo=info["tipo"],
                    motivo=info["motivo"],
                ))
                creados += 1

    with transaction.atomic():
        BloqueoMedico.objects.all().delete()
        BloqueoMedico.objects.bulk_create(nuevos)
        resolvedor.guardar_ids_aprendidos()

    return creados, omitidos
