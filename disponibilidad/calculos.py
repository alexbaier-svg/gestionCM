"""Cálculos compartidos sobre oferta/bloqueos de médicos (usados por la agenda
diaria, el mapa de calor de ocupación y la vista de oferta por médico)."""

from .models import BloqueoMedico


def minutos_brutos(ofertas):
    """Minutos totales de las ventanas de oferta, sin descontar bloqueos."""
    return sum(
        (o.hora_fin.hour * 60 + o.hora_fin.minute) - (o.hora_inicio.hour * 60 + o.hora_inicio.minute)
        for o in ofertas
    )


def minutos_libres(ofertas, bloqueos):
    """Minutos netos disponibles de un médico un día: sus ventanas de oferta,
    descontando lo que cubren sus bloqueos ese mismo día."""
    if any(b.tipo == BloqueoMedico.Tipo.DIA_COMPLETO for b in bloqueos):
        return 0

    total = 0
    for oferta in ofertas:
        segmentos = [(oferta.hora_inicio.hour * 60 + oferta.hora_inicio.minute,
                      oferta.hora_fin.hour * 60 + oferta.hora_fin.minute)]
        for b in bloqueos:
            bi = b.hora_inicio.hour * 60 + b.hora_inicio.minute
            bf = b.hora_fin.hour * 60 + b.hora_fin.minute
            nuevos = []
            for si, sf in segmentos:
                if bf <= si or bi >= sf:
                    nuevos.append((si, sf))
                    continue
                if bi > si:
                    nuevos.append((si, bi))
                if bf < sf:
                    nuevos.append((bf, sf))
            segmentos = nuevos
        total += sum(sf - si for si, sf in segmentos)
    return total


def inicio_semana(fecha):
    """Lunes de la semana de `fecha` (el domingo cuenta como la semana siguiente)."""
    import datetime

    if fecha.weekday() == 6:
        return fecha + datetime.timedelta(days=1)
    return fecha - datetime.timedelta(days=fecha.weekday())


def guardar_historial_semana(inicio, ofertas=None, bloqueos=None):
    """Regraba en OfertaDiaria las fechas lunes-sábado de la semana que parte en
    `inicio`, a partir de la oferta y los bloqueos dados (por defecto, los vigentes en
    la base). Es idempotente: reimportar la misma semana reemplaza sus filas."""
    import datetime
    from collections import defaultdict

    from medicos.models import Medico

    from .models import OfertaDiaria, OfertaMedico

    ofertas = OfertaMedico.objects.all() if ofertas is None else ofertas
    bloqueos = BloqueoMedico.objects.all() if bloqueos is None else bloqueos
    of, bl = defaultdict(list), defaultdict(list)
    for o in ofertas:
        of[(o.medico_id, o.dia_semana)].append(o)
    for b in bloqueos:
        bl[(b.medico_id, b.dia_semana)].append(b)

    duraciones = dict(Medico.objects.values_list("id", "duracion_consulta_min"))
    fechas = [inicio + datetime.timedelta(days=d) for d in range(6)]
    nuevas = []
    for (medico_id, dia), lista in of.items():
        if dia > 5:
            continue
        duracion = duraciones.get(medico_id) or 15
        brutos = minutos_brutos(lista)
        libres = minutos_libres(lista, bl.get((medico_id, dia), []))
        if brutos // duracion == 0:
            continue
        nuevas.append(OfertaDiaria(
            medico_id=medico_id,
            fecha=fechas[dia],
            oferta=brutos // duracion,
            bloqueos=(brutos - libres) // duracion,
        ))
    from django.db import transaction

    with transaction.atomic():
        OfertaDiaria.objects.filter(fecha__in=fechas).delete()
        OfertaDiaria.objects.bulk_create(nuevas)
    return len(nuevas)
