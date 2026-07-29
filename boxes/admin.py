from django.contrib import admin

from .models import AsignacionBox, Box


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ["nombre", "area", "ubicacion", "activo"]
    list_filter = ["area", "activo"]
    search_fields = ["nombre", "ubicacion"]


@admin.register(AsignacionBox)
class AsignacionBoxAdmin(admin.ModelAdmin):
    list_display = ["medico", "box", "dia_semana"]
    list_filter = ["box", "dia_semana"]
    autocomplete_fields = ["medico", "box"]
    search_fields = ["medico__nombre_completo", "box__nombre"]
