from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def nettoyer_ids_utilisateur_orphelins(apps, schema_editor):
    Ruche = apps.get_model("rucheapp", "Ruche")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".", 1)
    Utilisateur = apps.get_model(app_label, model_name)
    ids_valides = Utilisateur.objects.values_list("pk", flat=True)
    Ruche.objects.exclude(user_id__isnull=True).exclude(user_id__in=ids_valides).update(
        user_id=None
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rucheapp", "0004_ruche_qr_token"),
    ]

    operations = [
        migrations.RunPython(
            nettoyer_ids_utilisateur_orphelins,
            migrations.RunPython.noop,
        ),
        migrations.RenameField(
            model_name="ruche",
            old_name="user_id",
            new_name="user",
        ),
        migrations.AlterField(
            model_name="ruche",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="user_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ruches",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ID utilisateur",
            ),
        ),
    ]
