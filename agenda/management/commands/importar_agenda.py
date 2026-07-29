"""Importa un archivo de citas exportado desde el sistema externo del centro médico.

Formato observado: CSV en UTF-16, separado por comas, con columnas como
'Profesional/Recurso', 'No. Documento Profesional', 'Especialidad', 'Fecha desde',
'Hora desde', 'Fecha hasta', 'Hora hasta', 'Estado', 'AppointmentId', entre otras.

La lógica de parseo vive en agenda/importador.py (compartida con la vista web de
importación); este comando solo se encarga de leer el archivo desde disco.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from agenda.importador import importar_agenda_csv


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

        with archivo:
            nombre_archivo = ruta.split("/")[-1].split("\\")[-1]
            importacion = importar_agenda_csv(archivo, nombre_archivo, usuario)

        self.stdout.write(self.style.SUCCESS(
            f"Importación completa: {importacion.filas_procesadas} filas procesadas, "
            f"{importacion.filas_omitidas} omitidas."
        ))
