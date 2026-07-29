"""Crea los grupos de roles del sistema (Administrador, Recepción, Médico) con sus
permisos base. Idempotente: se puede volver a ejecutar sin duplicar nada.

Uso: python manage.py configurar_roles
"""

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand

from agenda.models import BloqueAgenda, ImportacionAgenda
from boxes.models import AsignacionBox, Box
from medicos.models import Especialidad, Medico

ADMIN_MODELOS = [Medico, Especialidad, Box, AsignacionBox, BloqueAgenda, ImportacionAgenda, User]
ADMIN_ACCIONES = ["add", "change", "delete", "view"]

RECEPCION_PERMISOS = [
    ("view", BloqueAgenda),
    ("view", Medico),
    ("view", Box),
]

MEDICO_PERMISOS = [
    ("view", BloqueAgenda),
]


def _permiso(accion, modelo):
    codename = f"{accion}_{modelo._meta.model_name}"
    return Permission.objects.get(content_type__app_label=modelo._meta.app_label, codename=codename)


class Command(BaseCommand):
    help = "Crea/actualiza los grupos Administrador, Recepción y Médico con sus permisos."

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name="Administrador")
        admin_perms = [_permiso(accion, modelo) for modelo in ADMIN_MODELOS for accion in ADMIN_ACCIONES]
        admin_group.permissions.set(admin_perms)

        recepcion_group, _ = Group.objects.get_or_create(name="Recepción")
        recepcion_group.permissions.set([_permiso(a, m) for a, m in RECEPCION_PERMISOS])

        medico_group, _ = Group.objects.get_or_create(name="Médico")
        medico_group.permissions.set([_permiso(a, m) for a, m in MEDICO_PERMISOS])

        self.stdout.write(self.style.SUCCESS(
            "Roles configurados: Administrador, Recepción, Médico."
        ))
