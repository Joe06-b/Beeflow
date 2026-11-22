from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rucheapp", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ruche",
            name="user_id",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="user_id"),
        ),
        migrations.RenameField(
            model_name="ruche",
            old_name="id_environnement",
            new_name="idZone",
        ),
        migrations.AlterField(
            model_name="ruche",
            name="idZone",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="idZone"),
        ),
    ]
