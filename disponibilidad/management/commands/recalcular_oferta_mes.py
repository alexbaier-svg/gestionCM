"""Recalcula oferta y bloqueos (en citas) de un mes, semana por semana, por
especialidad, usando archivos ExportarOferta / ExportarBloqueos y el plantel de
médicos activos actual. No toca las tablas vigentes (OfertaMedico/BloqueoMedico).

Uso (ver REUNIONES.md, sección "Scripts"):
  python manage.py recalcular_oferta_mes --mes 2026-11 \
      --oferta ExportarOferta-20261110.xlsx --bloqueos ExportarBloqueos-20261109.xlsx \
      --salida semanas_nov.json --guardar-historial

Para una semana con otros archivos (comparación justa con una semana ya cerrada):
  ... --solo-lunes 2026-11-02 --oferta ExportarOferta-20261103.xlsx \
      --bloqueos ExportarBloqueos-20261103.xlsx --salida semanas_nov.json
(--salida mezcla con el JSON existente, solo reemplaza las semanas calculadas.)
"""

import datetime
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from disponibilidad.calculos import guardar_historial_semana, minutos_brutos, minutos_libres
from disponibilidad.importador import importar_bloqueos_xlsx, importar_oferta_xlsx
from disponibilidad.models import OfertaDiaria
from medicos.models import Medico


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").upper()


def grupo(e):
    """Agrupa especialidades como en las diapositivas de reunión (e ya normalizada)."""
    if "TRAUMATOLOG" in e or "TRAMATOLOG" in e: return "TRAUMATOLOGIA"
    if e.startswith("CIRUGIA") or e == "CIRUJANO": return "CIRUGIA"
    if e == "COLOPROCTOLOGIA": return "COLOPROCTOLOGO"
    if "NEUROCIRUJ" in e: return "NEUROCIRUGIA"
    if "FORMACION" in e: return "MEDICINA GENERAL"
    if e.startswith("GINECOLOGIA") or e.startswith("ECOGRAFISTA"): return "GINECOLOGIA"
    if e.startswith("NEUROLOGIA"): return "NEUROLOGIA"
    if e.startswith("PEDIATRIA"): return "PEDIATRIA"
    if e.startswith("FISIATR"): return "FISIATRIA"
    if e.startswith("MEDINA FAMILIAR"): return "MEDICINA FAMILIAR"
    if e.startswith("MEDICINA INTERNA /"): return "NEFROLOGIA"
    return e


class Command(BaseCommand):
    help = "Recalcula oferta/bloqueos de un mes por semana y especialidad (opcionalmente regraba el historial)."

    def add_arguments(self, parser):
        parser.add_argument("--mes", required=True, help="YYYY-MM")
        parser.add_argument("--oferta", required=True, help="Ruta a ExportarOferta-*.xlsx")
        parser.add_argument("--bloqueos", required=True, help="Ruta a ExportarBloqueos-*.xlsx")
        parser.add_argument("--solo-lunes", action="append", default=[],
                            help="YYYY-MM-DD de un lunes; repetible. Si se omite, todas las semanas del mes.")
        parser.add_argument("--salida", help="JSON de salida (se mezcla con el existente).")
        parser.add_argument("--guardar-historial", action="store_true",
                            help="Regraba OfertaDiaria (menú Oferta médicos) para esas semanas.")

    def handle(self, *args, **o):
        anio, mes = (int(x) for x in o["mes"].split("-"))
        of_bytes = Path(o["oferta"]).read_bytes()
        bl_bytes = Path(o["bloqueos"]).read_bytes()

        medicos = {}
        for m in Medico.objects.filter(activo=True).prefetch_related("especialidades"):
            esp = [_norm(e.nombre) for e in m.especialidades.all()]
            medicos[m.id] = (grupo(esp[0]) if esp else "SIN ESPECIALIDAD", m.duracion_consulta_min or 15)

        if o["solo_lunes"]:
            lunes_lista = [datetime.date.fromisoformat(x) for x in o["solo_lunes"]]
        else:
            primero = datetime.date(anio, mes, 1)
            ultimo = (primero + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
            d = primero - datetime.timedelta(days=primero.weekday())  # lunes de la semana del día 1
            lunes_lista = []
            while d <= ultimo:
                if d + datetime.timedelta(days=5) >= primero:  # la semana tiene algún lun–sáb del mes
                    lunes_lista.append(d)
                d += datetime.timedelta(days=7)

        semanas = {}
        for lunes in lunes_lista:
            ofs = importar_oferta_xlsx(of_bytes, fecha_referencia=lunes, solo_calcular=True)
            bls = importar_bloqueos_xlsx(bl_bytes, fecha_referencia=lunes,
                                        fecha_hasta_referencia=lunes + datetime.timedelta(days=6),
                                        solo_calcular=True)
            of = defaultdict(list); bl = defaultdict(list)
            for x in ofs: of[(x.medico_id, x.dia_semana)].append(x)
            for x in bls: bl[(x.medico_id, x.dia_semana)].append(x)
            res = defaultdict(lambda: [0, 0])
            for (mid, dia), lista in of.items():
                fecha = lunes + datetime.timedelta(days=dia)
                if dia > 5 or fecha.month != mes or fecha.year != anio or mid not in medicos:
                    continue  # solo lun–sáb del mes pedido y médicos del plantel activo
                g, dur = medicos[mid]
                br = minutos_brutos(lista)
                li = minutos_libres(lista, bl.get((mid, dia), []))
                res[g][0] += br // dur
                res[g][1] += (br - li) // dur
            semanas[str(lunes)] = dict(res)
            if o["guardar_historial"]:
                guardar_historial_semana(lunes, ofertas=ofs, bloqueos=bls)
            self.stdout.write(f"{lunes}: oferta {sum(v[0] for v in res.values())} / "
                              f"bloqueos {sum(v[1] for v in res.values())}")

        if o["salida"]:
            ruta = Path(o["salida"])
            previo = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
            previo.update(semanas)
            ruta.write_text(json.dumps(previo, ensure_ascii=False, indent=1), encoding="utf-8")
            self.stdout.write(f"JSON guardado en {ruta}")
        if o["guardar_historial"]:
            tot = OfertaDiaria.objects.filter(fecha__year=anio, fecha__month=mes).aggregate(o=Sum("oferta"), b=Sum("bloqueos"))
            self.stdout.write(f"Historial {o['mes']}: oferta {tot['o']} / bloqueos {tot['b']}")
