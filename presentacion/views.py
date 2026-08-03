from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .data import obtener_diapositivas

ALTURA_MAX_BARRA_PX = 160


def _es_administrador(user):
    return user.is_superuser or user.groups.filter(name="Administrador").exists()


def _armar_grafico(categorias, series):
    """Arma la estructura del gráfico de barras con el alto de cada barra ya
    calculado en píxeles (no %: dentro de un contenedor flex, una altura en %
    queda sujeta a flex-shrink y termina comprimiendo todas las barras a un
    tamaño parecido en vez de respetar la escala real)."""
    max_valor = max(v for s in series for v in s["valores"]) or 1
    grupos = []
    for i, categoria in enumerate(categorias):
        barras = [
            {
                "nombre": s["nombre"],
                "valor": s["valores"][i],
                "color": s["color"],
                "alto_px": round(s["valores"][i] / max_valor * ALTURA_MAX_BARRA_PX),
            }
            for s in series
        ]
        grupos.append({"categoria": categoria, "barras": barras})
    return grupos


def _aplicar_altura_px_grupos(grupos):
    """Igual que _armar_grafico pero para series ya expresadas en % (0-100),
    como en la diapositiva de Experiencia Paciente."""
    for grupo in grupos:
        for serie in grupo["series"]:
            serie["alto_px"] = round(serie["pct"] / 100 * ALTURA_MAX_BARRA_PX)
    return grupos


@login_required
def visor(request):
    if not _es_administrador(request.user):
        raise PermissionDenied

    diapositivas = obtener_diapositivas()
    total = len(diapositivas)

    try:
        numero = int(request.GET.get("diapositiva", 1))
    except ValueError:
        numero = 1
    numero = max(1, min(numero, total))

    actual = diapositivas[numero - 1]
    datos = dict(actual["contexto"])
    if "categorias" in datos and "series" in datos:
        datos["grafico"] = _armar_grafico(datos["categorias"], datos["series"])
    if "grupos" in datos:
        datos["grupos"] = _aplicar_altura_px_grupos(datos["grupos"])

    contexto = {
        "numero": numero,
        "total": total,
        "titulo": actual["titulo"],
        "plantilla_diapositiva": actual["plantilla"],
        "datos": datos,
        "anterior": numero - 1 if numero > 1 else None,
        "siguiente": numero + 1 if numero < total else None,
        "indices": range(1, total + 1),
    }
    return render(request, "presentacion/visor.html", contexto)
