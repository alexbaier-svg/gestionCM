"""Actualiza diapositivas de oferta/bloqueos de reuniones ya creadas, a partir del
JSON que genera `recalcular_oferta_mes`.

  - Reunión semanal (--semanal FECHA): diapositivas 2 (oferta por especialidad de la
    semana FECHA), 3 (comparativo vs semana anterior + acumulado) y 4 (oferta efectiva
    de la semana anterior).
  - Reunión de cierre (--cierre FECHA): diapositivas 6 (proyección del mes completo)
    y 7 (comparativo vs mes anterior; requiere --mes-anterior-oferta/--bloqueos).

Ejemplo:
  python manage.py actualizar_reunion --semanas semanas_nov.json \
      --semanal 2026-11-09 --semana-anterior 2026-11-02 \
      --cierre 2026-11-02 --mes-anterior-oferta 14200 --mes-anterior-bloqueos 1389
Los números se escriben en el contexto (solo las claves necesarias).
"""

import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from presentacion.models import Diapositiva


def _f(n):
    return f"{n:,}".replace(",", ".")


def _p(x):
    v = round(x, 1)
    return (str(int(v)) if v == int(v) else str(v)) + "%"


def _filas(res):
    filas, tb, tl = [], 0, 0
    for k in sorted(res):
        br, bq = res[k]
        if br == 0 and bq == 0:
            continue
        tb += br; tl += bq
        filas.append({"pct": _p(bq / br * 100 if br else 0), "bruta": _f(br), "bloqueos": _f(bq),
                      "efectiva": _f(br - bq), "especialidad": k})
    top = max((x for x in filas if x["bruta"] != "0"), key=lambda x: float(x["pct"][:-1]))
    return filas, tb, tl, top


def _aplicar_oferta(c, filas, tb, tl, top):
    pct = round(tl / tb * 100, 1)
    c["kpis"][0]["valor"] = _f(tb); c["kpis"][1]["valor"] = _f(tl); c["kpis"][2]["valor"] = f"{pct}%"
    c["kpis"][3].update({"valor": top["especialidad"], "detalle": f"{top['pct']} de bloqueo"})
    c["filas"] = filas
    c["total"].update({"pct": f"{pct}%", "bruta": _f(tb), "bloqueos": _f(tl), "efectiva": _f(tb - tl)})
    return pct


def _diap(fecha, orden):
    try:
        return Diapositiva.objects.get(reunion__fecha=fecha, orden=orden)
    except Diapositiva.DoesNotExist:
        raise CommandError(f"No existe la diapositiva {orden} de la reunión {fecha}.")


class Command(BaseCommand):
    help = "Actualiza las diapositivas de oferta/bloqueos de una reunión semanal y/o de cierre."

    def add_arguments(self, parser):
        parser.add_argument("--semanas", required=True, help="JSON de recalcular_oferta_mes")
        parser.add_argument("--semanal", help="Fecha (lunes) de la reunión semanal, YYYY-MM-DD")
        parser.add_argument("--semana-anterior", help="Lunes de la semana anterior (comparativo)")
        parser.add_argument("--cierre", help="Fecha de la reunión de cierre con la proyección del mes")
        parser.add_argument("--mes-anterior-oferta", type=int)
        parser.add_argument("--mes-anterior-bloqueos", type=int)

    def handle(self, *args, **o):
        S = json.loads(Path(o["semanas"]).read_text(encoding="utf-8"))

        if o["semanal"]:
            fecha = o["semanal"]
            if fecha not in S:
                raise CommandError(f"La semana {fecha} no está en el JSON.")
            filas, tb, tl, top = _filas({k: list(v) for k, v in S[fecha].items()})
            d = _diap(fecha, 2); c = d.contexto
            pct = _aplicar_oferta(c, filas, tb, tl, top); d.contexto = c; d.save()
            msg = f"{fecha}: oferta {tb} / bloqueos {tl} = {pct}% (top {top['especialidad']} {top['pct']})"
            ant = o["semana_anterior"]
            if ant:
                ab = sum(v[0] for v in S[ant].values()); al = sum(v[1] for v in S[ant].values())
                ant_pct = round(al / ab * 100, 1); acu = round((al + tl) / (ab + tb) * 100, 1)
                d = _diap(fecha, 3); c = d.contexto
                c["kpis"][0]["valor"] = f"{ant_pct}%"; c["kpis"][1]["valor"] = f"{pct}%"
                c["kpis"][2]["valor"] = str(acu).replace(".", ",") + "%"
                c["series"][0]["valores"] = [ab, tb]
                c["series"][1]["valores"] = [ab - al, tb - tl]
                c["series"][2]["valores"] = [al, tl]
                c["kpi_destacado"]["valor"] = f"{round(pct - ant_pct, 1)} pts"
                d.contexto = c; d.save()
                d = _diap(fecha, 4); c = d.contexto
                c["ventas_semanales"][0]["oferta_efectiva"] = ab - al
                d.contexto = c; d.save()
                msg += f" | anterior {ab}/{al} = {ant_pct}% | acumulado {acu}%"
            self.stdout.write(msg)

        if o["cierre"]:
            mes = defaultdict(lambda: [0, 0])
            for sem in S.values():
                for k, v in sem.items():
                    mes[k][0] += v[0]; mes[k][1] += v[1]
            filas, tb, tl, top = _filas(mes)
            d = _diap(o["cierre"], 6); c = d.contexto
            pct = _aplicar_oferta(c, filas, tb, tl, top); d.contexto = c; d.save()
            msg = f"cierre {o['cierre']}: oferta {tb} / bloqueos {tl} = {pct}% (top {top['especialidad']} {top['pct']})"
            if o["mes_anterior_oferta"] and o["mes_anterior_bloqueos"] is not None:
                ob, ol = o["mes_anterior_oferta"], o["mes_anterior_bloqueos"]
                opct = round(ol / ob * 100, 1)
                d = _diap(o["cierre"], 7); c = d.contexto
                c["kpis"][1]["valor"] = f"{pct}%"
                c["series"][0]["valores"] = [ob, tb]
                c["series"][1]["valores"] = [ob - ol, tb - tl]
                c["series"][2]["valores"] = [ol, tl]
                c["kpi_destacado"]["valor"] = f"{round(pct - opct, 1)} pts"
                d.contexto = c; d.save()
                msg += f" | vs mes anterior {round(pct - opct, 1)} pts"
            self.stdout.write(msg)
