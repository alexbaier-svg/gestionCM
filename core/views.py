from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    accesos = []
    if request.user.has_perm("medicos.view_medico"):
        accesos.append({
            "titulo": "Médicos",
            "descripcion": "Ver, agregar y editar médicos.",
            "url": "medicos:listar",
            "icono": "🩺",
        })
    if request.user.has_perm("boxes.view_box"):
        accesos.append({
            "titulo": "Boxes",
            "descripcion": "Ver, agregar y editar boxes por piso.",
            "url": "boxes:listar",
            "icono": "🚪",
        })
    accesos.append({
        "titulo": "Distribución",
        "descripcion": "Ver qué médico tiene cada box, por piso.",
        "url": "boxes:distribucion",
        "icono": "🗺️",
    })
    accesos.append({
        "titulo": "Agenda diaria",
        "descripcion": "Ver y exportar la agenda de un día.",
        "url": "agenda:diaria",
        "icono": "📅",
    })
    if request.user.has_perm("agenda.add_bloqueagenda"):
        accesos.append({
            "titulo": "Importar agenda",
            "descripcion": "Subir el archivo de citas del otro sistema.",
            "url": "agenda:importar",
            "icono": "⬆️",
        })
    return render(request, "core/dashboard.html", {"accesos": accesos})
