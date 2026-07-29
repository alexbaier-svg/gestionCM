from django import forms


class ImportarAgendaForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo de citas (CSV)",
        help_text="El archivo exportado por el otro sistema, ej. ExportarCitas-20260728.csv",
    )
