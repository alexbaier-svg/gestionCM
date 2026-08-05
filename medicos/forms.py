from django import forms

from .models import Especialidad, Medico


class EspecialidadForm(forms.ModelForm):
    class Meta:
        model = Especialidad
        fields = ["nombre"]
        labels = {"nombre": "Nombre"}


class MedicoForm(forms.ModelForm):
    class Meta:
        model = Medico
        fields = [
            "nombre_completo", "rut", "especialidades", "telefono", "email",
            "duracion_consulta_min", "activo",
        ]
        widgets = {
            "especialidades": forms.CheckboxSelectMultiple,
        }
        labels = {
            "nombre_completo": "Nombre completo",
            "rut": "RUT",
            "especialidades": "Especialidad(es)",
            "telefono": "Teléfono",
            "email": "Correo electrónico",
            "duracion_consulta_min": "Duración de consulta (minutos)",
            "activo": "Activo",
        }
