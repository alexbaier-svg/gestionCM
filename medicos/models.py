from django.conf import settings
from django.db import models


class Especialidad(models.Model):
    nombre = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Medico(models.Model):
    nombre_completo = models.CharField(max_length=200)
    rut = models.CharField(
        "RUT", max_length=20, unique=True,
        help_text="Coincide con 'No. Documento Profesional' del archivo importado.",
    )
    especialidades = models.ManyToManyField(Especialidad, related_name="medicos", blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    duracion_consulta_min = models.PositiveSmallIntegerField(
        "Duración de consulta (min)", default=15,
        help_text="Usada para estimar cuántas citas caben en su oferta horaria de un día.",
    )
    activo = models.BooleanField(default=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="medico",
        help_text="Cuenta de usuario vinculada, para que el médico vea solo su propia agenda.",
    )

    class Meta:
        verbose_name = "Médico"
        verbose_name_plural = "Médicos"
        ordering = ["nombre_completo"]

    def __str__(self):
        return self.nombre_completo
