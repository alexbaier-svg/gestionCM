from django.conf import settings
from django.db import models


class ImportacionAgenda(models.Model):
    archivo_nombre = models.CharField(max_length=255)
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    filas_procesadas = models.PositiveIntegerField(default=0)
    filas_omitidas = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Importación de Agenda"
        verbose_name_plural = "Importaciones de Agenda"
        ordering = ["-fecha_importacion"]

    def __str__(self):
        return f"{self.archivo_nombre} ({self.fecha_importacion:%Y-%m-%d %H:%M})"


class BloqueAgenda(models.Model):
    class Estado(models.TextChoices):
        CITADO = "citado", "Citado"
        CONFIRMADO = "confirmado", "Confirmado"
        ANULADO = "anulado", "Anulado"
        BLOQUEADO = "bloqueado", "Bloqueado"
        ATENDIDO = "atendido", "Atendido"
        OTRO = "otro", "Otro"

    class Origen(models.TextChoices):
        IMPORTADO = "importado", "Importado"
        MANUAL = "manual", "Manual"

    medico = models.ForeignKey(
        "medicos.Medico", on_delete=models.CASCADE, related_name="bloques_agenda"
    )
    box = models.ForeignKey(
        "boxes.Box", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bloques_agenda",
        help_text="Se propone automáticamente según la asignación fija del médico; "
                   "puede reasignarse manualmente.",
    )
    especialidad = models.CharField(max_length=150, blank=True)
    id_externo = models.CharField(
        "ID externo", max_length=64, null=True, blank=True, unique=True,
        help_text="AppointmentId del sistema origen, solo para evitar duplicar al reimportar. "
                   "No es dato de paciente.",
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.CITADO)
    origen = models.CharField(max_length=20, choices=Origen.choices, default=Origen.MANUAL)
    importacion = models.ForeignKey(
        ImportacionAgenda, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bloques",
    )

    class Meta:
        verbose_name = "Bloque de Agenda"
        verbose_name_plural = "Bloques de Agenda"
        ordering = ["fecha", "hora_inicio"]
        indexes = [
            models.Index(fields=["fecha", "medico"]),
            models.Index(fields=["fecha", "box"]),
        ]

    def __str__(self):
        return f"{self.medico} — {self.fecha} {self.hora_inicio}-{self.hora_fin}"
