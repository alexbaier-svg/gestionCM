from django.contrib import admin

from .models import Especialidad, Medico


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ["nombre_completo", "rut", "activo", "telefono", "email"]
    list_filter = ["activo", "especialidades"]
    search_fields = ["nombre_completo", "rut"]
    filter_horizontal = ["especialidades"]
    autocomplete_fields = ["usuario"]
