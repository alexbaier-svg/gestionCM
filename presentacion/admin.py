from django.contrib import admin

from .models import Diapositiva, Reunion


class DiapositivaInline(admin.TabularInline):
    model = Diapositiva
    extra = 0


@admin.register(Reunion)
class ReunionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "titulo", "creado_en")
    inlines = [DiapositivaInline]
