from django import forms


class ImportarOfertaForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo de oferta (Excel)",
        help_text="El archivo exportado por el otro sistema, ej. ExportarOferta-20260729.xlsx",
    )


class ImportarBloqueosForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo de bloqueos (Excel)",
        help_text="El archivo exportado por el otro sistema, ej. ExportarBloqueos-20260729.xlsx",
    )
