from django.db import models


class Box(models.Model):
    class Area(models.TextChoices):
        CONSULTA = "consulta", "Consulta Presencial"
        IMAGENES = "imagenes", "Imágenes"
        PROCEDIMIENTOS = "procedimientos", "Procedimientos"
        OTRO = "otro", "Otro"

    nombre = models.CharField(max_length=100, unique=True)
    area = models.CharField(max_length=20, choices=Area.choices, default=Area.CONSULTA)
    ubicacion = models.CharField(max_length=150, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Box"
        verbose_name_plural = "Boxes"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class AsignacionBox(models.Model):
    """Regla fija: box(es) por defecto de un médico, usada para proponer
    automáticamente el box al importar una agenda diaria."""

    medico = models.ForeignKey(
        "medicos.Medico", on_delete=models.CASCADE, related_name="asignaciones_box"
    )
    box = models.ForeignKey(Box, on_delete=models.CASCADE, related_name="asignaciones")
    dia_semana = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="0=Lunes ... 6=Domingo. Vacío = aplica todos los días.",
    )

    class Meta:
        verbose_name = "Asignación de Box"
        verbose_name_plural = "Asignaciones de Box"
        unique_together = ("medico", "box", "dia_semana")

    def __str__(self):
        return f"{self.medico} → {self.box}"
