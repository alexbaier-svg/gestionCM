from django.db import models


class OfertaMedico(models.Model):
    """Franja horaria recurrente en la que un médico atiende, según el archivo
    'ExportarOferta' del sistema externo. Se reemplaza por completo en cada
    importación (representa el estado vigente, no un historial)."""

    medico = models.ForeignKey(
        "medicos.Medico", on_delete=models.CASCADE, related_name="ofertas"
    )
    dia_semana = models.PositiveSmallIntegerField(help_text="0=Lunes ... 6=Domingo.")
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        verbose_name = "Oferta de médico"
        verbose_name_plural = "Ofertas de médico"
        ordering = ["dia_semana", "hora_inicio"]

    def __str__(self):
        return f"{self.medico} — día {self.dia_semana} {self.hora_inicio}-{self.hora_fin}"


class BloqueoMedico(models.Model):
    """Período en que un médico NO atiende (ausencia), según el archivo
    'ExportarBloqueos'. Se reemplaza por completo en cada importación."""

    class Tipo(models.TextChoices):
        PARCIAL = "Partial", "Parcial"
        DIA_COMPLETO = "WholeDay", "Día completo"

    medico = models.ForeignKey(
        "medicos.Medico", on_delete=models.CASCADE, related_name="bloqueos"
    )
    dia_semana = models.PositiveSmallIntegerField(help_text="0=Lunes ... 6=Domingo.")
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PARCIAL)
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Bloqueo de médico"
        verbose_name_plural = "Bloqueos de médico"
        ordering = ["dia_semana", "hora_inicio"]

    def __str__(self):
        return f"{self.medico} — día {self.dia_semana} {self.hora_inicio}-{self.hora_fin}"
