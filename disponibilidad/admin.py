from django.contrib import admin

from .models import BloqueoMedico, OfertaDiaria, OfertaMedico


@admin.register(OfertaMedico)
class OfertaMedicoAdmin(admin.ModelAdmin):
    list_display = ["medico", "dia_semana", "hora_inicio", "hora_fin"]
    list_filter = ["dia_semana"]
    search_fields = ["medico__nombre_completo"]


@admin.register(BloqueoMedico)
class BloqueoMedicoAdmin(admin.ModelAdmin):
    list_display = ["medico", "dia_semana", "hora_inicio", "hora_fin", "tipo", "motivo"]
    list_filter = ["dia_semana", "tipo"]
    search_fields = ["medico__nombre_completo", "motivo"]


@admin.register(OfertaDiaria)
class OfertaDiariaAdmin(admin.ModelAdmin):
    list_display = ["medico", "fecha", "oferta", "bloqueos"]
    list_filter = ["fecha"]
    search_fields = ["medico__nombre_completo"]
