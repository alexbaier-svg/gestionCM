from django import forms
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from medicos.models import Medico

ROLES = ["Administrador", "Recepción", "Médico"]


class UsuarioForm(forms.ModelForm):
    rol = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=ROLES),
        label="Rol",
        empty_label=None,
    )
    medico = forms.ModelChoiceField(
        queryset=Medico.objects.all().order_by("nombre_completo"),
        required=False,
        label="Médico vinculado (obligatorio solo si el rol es Médico)",
    )
    password1 = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput, required=False,
        help_text="Déjalo en blanco al editar si no quieres cambiarla.",
    )
    password2 = forms.CharField(
        label="Confirmar contraseña", widget=forms.PasswordInput, required=False,
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "is_active"]
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "email": "Correo electrónico",
            "is_active": "Activo",
        }

    def __init__(self, *args, es_nuevo=False, **kwargs):
        self.es_nuevo = es_nuevo
        super().__init__(*args, **kwargs)
        if self.es_nuevo:
            self.fields["password1"].required = True
            self.fields["password2"].required = True
        if self.instance.pk:
            grupo_actual = self.instance.groups.filter(name__in=ROLES).first()
            if grupo_actual:
                self.fields["rol"].initial = grupo_actual.pk
            medico_actual = getattr(self.instance, "medico", None)
            if medico_actual:
                self.fields["medico"].initial = medico_actual.pk

    def clean(self):
        limpio = super().clean()
        p1, p2 = limpio.get("password1"), limpio.get("password2")
        if p1 or p2 or self.es_nuevo:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif p1:
                try:
                    validate_password(p1)
                except ValidationError as exc:
                    self.add_error("password1", exc)
        rol = limpio.get("rol")
        medico = limpio.get("medico")
        if rol and rol.name == "Médico" and not medico:
            self.add_error("medico", "Selecciona el médico vinculado para el rol Médico.")
        return limpio

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.is_staff = True
        password = self.cleaned_data.get("password1")
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
            rol = self.cleaned_data["rol"]
            usuario.groups.set([rol])
            medico = self.cleaned_data.get("medico")
            Medico.objects.filter(usuario=usuario).exclude(
                pk=getattr(medico, "pk", None)
            ).update(usuario=None)
            if medico:
                medico.usuario = usuario
                medico.save(update_fields=["usuario"])
        return usuario
