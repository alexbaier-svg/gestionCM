from django.db import models


class Reunion(models.Model):
    fecha = models.DateField("Fecha de la reunión", unique=True)
    titulo = models.CharField("Título", max_length=200, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Reunión"
        verbose_name_plural = "Reuniones"

    def __str__(self):
        return self.titulo or f"Reunión del {self.fecha:%d-%m-%Y}"


class Diapositiva(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.CASCADE, related_name="diapositivas")
    orden = models.PositiveSmallIntegerField()
    titulo = models.CharField("Título", max_length=200)
    plantilla = models.CharField("Plantilla", max_length=200)
    contexto = models.JSONField("Datos", default=dict)

    class Meta:
        ordering = ["orden"]
        unique_together = ("reunion", "orden")
        verbose_name = "Diapositiva"
        verbose_name_plural = "Diapositivas"

    def __str__(self):
        return f"{self.reunion} — {self.titulo}"
