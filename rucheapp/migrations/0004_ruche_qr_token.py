import uuid

from django.db import migrations, models


def attribuer_tokens_qr(apps, schema_editor):
    Ruche = apps.get_model("rucheapp", "Ruche")
    for ruche in Ruche.objects.filter(qr_token__isnull=True).iterator():
        ruche.qr_token = uuid.uuid4()
        ruche.save(update_fields=["qr_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("rucheapp", "0003_historiqueruche"),
    ]

    operations = [
        migrations.AddField(
            model_name="ruche",
            name="qr_token",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(attribuer_tokens_qr, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="ruche",
            name="qr_token",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
            ),
        ),
    ]
