"""Crea (o reemplaza) una Reunion y sus Diapositivas a partir de un archivo JSON.

Uso semanal: se arma un JSON con la estructura de abajo (uno nuevo cada semana, con
los datos ya calculados a partir de los Excel de Oferta/Bloqueos y lo demás que pida
el usuario) y se carga con:

    manage.py cargar_reunion archivo.json

Formato esperado del JSON:
{
  "fecha": "2026-08-17",
  "titulo": "Reunión semanal - 17/08/2026",
  "diapositivas": [
    {"titulo": "...", "plantilla": "presentacion/diapositivas/xxx.html", "contexto": {...}},
    ...
  ]
}

Cada reunión queda guardada de forma permanente (no se sobreescribe al cargar la
siguiente semana); usar --reemplazar solo para corregir una reunión ya cargada.
"""

import json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from presentacion.models import Diapositiva, Reunion


class Command(BaseCommand):
    help = "Crea una Reunion y sus Diapositivas a partir de un archivo JSON."

    def add_arguments(self, parser):
        parser.add_argument("archivo_json", type=str)
        parser.add_argument(
            "--reemplazar",
            action="store_true",
            help="Si ya existe una reunión con esa fecha, borra sus diapositivas y las vuelve a crear.",
        )

    def handle(self, *args, **options):
        with open(options["archivo_json"], encoding="utf-8") as f:
            datos = json.load(f)

        try:
            fecha = datetime.strptime(datos["fecha"], "%Y-%m-%d").date()
        except (KeyError, ValueError) as exc:
            raise CommandError("El JSON debe traer 'fecha' en formato YYYY-MM-DD.") from exc

        titulo = datos.get("titulo", "")
        diapositivas = datos.get("diapositivas", [])
        if not diapositivas:
            raise CommandError("El JSON debe traer al menos una diapositiva en 'diapositivas'.")

        with transaction.atomic():
            reunion, creada = Reunion.objects.get_or_create(fecha=fecha, defaults={"titulo": titulo})
            if not creada:
                if not options["reemplazar"]:
                    raise CommandError(
                        f"Ya existe una reunión con fecha {fecha}. Usa --reemplazar si quieres corregirla."
                    )
                reunion.titulo = titulo
                reunion.save(update_fields=["titulo"])
                reunion.diapositivas.all().delete()

            for orden, dia in enumerate(diapositivas, start=1):
                Diapositiva.objects.create(
                    reunion=reunion,
                    orden=orden,
                    titulo=dia["titulo"],
                    plantilla=dia["plantilla"],
                    contexto=dia.get("contexto", {}),
                )

        self.stdout.write(self.style.SUCCESS(
            f"Reunión '{reunion}' guardada con {len(diapositivas)} diapositivas."
        ))
