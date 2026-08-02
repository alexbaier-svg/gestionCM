from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .data import obtener_diapositivas


def _es_administrador(user):
    return user.is_superuser or user.groups.filter(name="Administrador").exists()


def _armar_grafico(categorias, series):
    """Arma la estructura del gráfico de barras con el alto de cada barra ya
    calculado como % del valor máximo, para no hacer cuentas en el template."""
    max_valor = max(v for s in series for v in s["valores"]) or 1
    grupos = []
    for i, categoria in enumerate(categorias):
        barras = [
            {
                "nombre": s["nombre"],
                "valor": s["valores"][i],
                "color": s["color"],
                # Como texto (no float) para que Django no lo formatee con coma
                # decimal (locale es-cl) y rompa el valor del CSS 'height'.
                "alto_pct": f"{s['valores'][i] / max_valor * 100:.1f}",
            }
            for s in series
        ]
        grupos.append({"categoria": categoria, "barras": barras})
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
