from django.contrib import admin
from import_export import resources
from import_export.admin import ExportActionMixin

from .models import BloqueAgenda, ImportacionAgenda


class AgendaDiariaResource(resources.ModelResource):
    """Resource usado para exportar el listado/agenda diaria: médico, horas y box."""

    medico = resources.Field(attribute="medico__nombre_completo", column_name="Médico")
    especialidad = resources.Field(attribute="especialidad", column_name="Especialidad")
    box = resources.Field(attribute="box__nombre", column_name="Box")
    fecha = resources.Field(attribute="fecha", column_name="Fecha")
    hora_inicio = resources.Field(attribute="hora_inicio", column_name="Hora inicio")
    hora_fin = resources.Field(attribute="hora_fin", column_name="Hora fin")
    estado = resources.Field(attribute="get_estado_display", column_name="Estado")

    class Meta:
        model = BloqueAgenda
        fields = ("medico", "especialidad", "box", "fecha", "hora_inicio", "hora_fin", "estado")
        export_order = fields


@admin.register(BloqueAgenda)
class BloqueAgendaAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_classes = [AgendaDiariaResource]
    list_display = [
        "fecha", "hora_inicio", "hora_fin", "medico", "box", "especialidad", "estado", "origen",
    ]
    list_filter = ["fecha", "box", "estado", "origen"]
    date_hierarchy = "fecha"
    search_fields = ["medico__nombre_completo", "especialidad"]
    autocomplete_fields = ["medico", "box"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        medico = getattr(request.user, "medico", None)
        if medico is not None and not request.user.is_superuser:
            # Rol Médico: solo ve su propia agenda.
            return qs.filter(medico=medico)
        return qs


@admin.register(ImportacionAgenda)
class ImportacionAgendaAdmin(admin.ModelAdmin):
    list_display = ["archivo_nombre", "fecha_importacion", "usuario", "filas_procesadas", "filas_omitidas"]
    readonly_fields = [f.name for f in ImportacionAgenda._meta.fields]

    def has_add_permission(self, request):
        return False
