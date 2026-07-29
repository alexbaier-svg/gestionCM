from django import forms

from .models import Medico


class MedicoForm(forms.ModelForm):
    class Meta:
        model = Medico
        fields = ["nombre_completo", "rut", "especialidades", "telefono", "email", "activo"]
        widgets = {
            "especialidades": forms.CheckboxSelectMultiple,
        }
        labels = {
            "nombre_completo": "Nombre completo",
            "rut": "RUT",
            "especialidades": "Especialidad(es)",
            "telefono": "Teléfono",
            "email": "Correo electrónico",
            "activo": "Activo",
        }
