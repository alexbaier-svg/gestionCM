"""Importa un archivo de citas exportado desde el sistema externo del centro médico.

Formato observado: CSV en UTF-16, separado por comas, con columnas como
'Profesional/Recurso', 'No. Documento Profesional', 'Especialidad', 'Fecha desde',
'Hora desde', 'Fecha hasta', 'Hora hasta', 'Estado', 'AppointmentId', entre otras.

Decisiones de diseño (ver CLAUDE.md):
- Se descartan explícitamente todos los datos de pacientes (PHI): nombre, RUT, teléfono,
  email, dirección, fecha de nacimiento no se leen ni almacenan.
- Solo se procesan filas cuyo 'Profesional/Recurso' coincide con un Médico ya registrado
  en el mantenedor (por RUT o, si no hay RUT, por nombre). Filas de recursos/equipos sin
  médico asociado se omiten.
- El box se propone automáticamente según la AsignacionBox (regla fija) del médico para
  ese día de la semana; si no hay regla, queda sin box para asignación manual posterior.
"""

import csv
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from agenda.models import BloqueAgenda, ImportacionAgenda
from boxes.models import AsignacionBox
from medicos.models import Medico

ESTADO_MAP = {
    "citado": BloqueAgenda.Estado.CITADO,
    "confirmado": BloqueAgenda.Estado.CONFIRMADO,
    "anulado": BloqueAgenda.Estado.ANULADO,
    "bloqueado": BloqueAgenda.Estado.BLOQUEADO,
    "atendido": BloqueAgenda.Estado.ATENDIDO,
}


def _norm(texto):
    return (texto or "").strip()


def _resolver_box(medico, fecha):
    dia_semana = fecha.weekday()
    asignacion = (
        AsignacionBox.objects.filter(medico=medico, dia_semana=dia_semana).first()
        or AsignacionBox.objects.filter(medico=medico, dia_semana__isnull=True).first()
    )
    return asignacion.box if asignacion else None


class Command(BaseCommand):
    help = "Importa una agenda diaria (CSV UTF-16) descartando datos de pacientes."

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=str, help="Ruta al archivo CSV a importar.")
        parser.add_argument(
            "--usuario", type=str, default=None,
            help="Username que queda registrado como responsable de la importación.",
        )
        parser.add_argument(
            "--encoding", type=str, default="utf-16-le",
            help="Encoding del archivo (por defecto utf-16-le, sin BOM, como exporta el "
                 "sistema origen).",
        )

    def handle(self, *args, **options):
        ruta = options["archivo"]
        usuario = None
        if options["usuario"]:
            User = get_user_model()
            try:
                usuario = User.objects.get(username=options["usuario"])
            except User.DoesNotExist:
                raise CommandError(f"Usuario '{options['usuario']}' no existe.")

        try:
            archivo = open(ruta, encoding=options["encoding"], newline="")
        except OSError as exc:
            raise CommandError(f"No se pudo abrir '{ruta}': {exc}")

        procesadas = 0
        omitidas = 0

        with archivo:
            lector = csv.DictReader(archivo)
            with transaction.atomic():
                importacion = ImportacionAgenda.objects.create(
                    archivo_nombre=ruta.split("/")[-1].split("\\")[-1],
                    usuario=usuario,
                )
                for fila in lector:
                    ok = self._procesar_fila(fila, importacion)
                    if ok:
                        procesadas += 1
                    else:
                        omitidas += 1
                importacion.filas_procesadas = procesadas
                importacion.filas_omitidas = omitidas
                importacion.save(update_fields=["filas_procesadas", "filas_omitidas"])

        self.stdout.write(self.style.SUCCESS(
            f"Importación completa: {procesadas} filas procesadas, {omitidas} omitidas."
        ))

    def _procesar_fila(self, fila, importacion):
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
