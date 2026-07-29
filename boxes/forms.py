from django import forms

from .models import Box


class BoxForm(forms.ModelForm):
    class Meta:
        model = Box
        fields = ["nombre", "piso", "area", "ubicacion", "activo"]
        labels = {
            "nombre": "Nombre",
            "piso": "Piso",
            "area": "Área",
            "ubicacion": "Ubicación",
            "activo": "Activo",
        }
