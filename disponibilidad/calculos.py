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
