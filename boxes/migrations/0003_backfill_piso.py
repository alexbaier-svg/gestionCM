import re

from django.db import migrations

PISO1_MAXIMO = 7  # Box 1 a 7 = Piso 1 (trauma). Box 8+ y boxes con nombre = Piso 2.


def backfill_piso(apps, schema_editor):
    Box = apps.get_model("boxes", "Box")
    for box in Box.objects.all():
        m = re.search(r"\d+", box.nombre)
        if box.nombre.strip().upper().startswith("BOX") and m and int(m.group()) <= PISO1_MAXIMO:
            box.piso = 1
        else:
            box.piso = 2
        box.save(update_fields=["piso"])


def sin_reversa(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('boxes', '0002_box_piso'),
    ]

    operations = [
        migrations.RunPython(backfill_piso, sin_reversa),
    ]
