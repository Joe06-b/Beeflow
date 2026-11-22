# Generated for the BeeFlow Ruche CRUD.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Ruche",
            fields=[
                ("id_ruche", models.AutoField(primary_key=True, serialize=False)),
                ("code_ruche", models.CharField(max_length=30, unique=True, verbose_name="Code de la ruche")),
                ("type_ruche", models.CharField(max_length=80, verbose_name="Type de ruche")),
                ("race_abeilles", models.CharField(max_length=100, verbose_name="Race des abeilles")),
                ("date_installation", models.DateField(verbose_name="Date d'installation")),
                ("presence_reine", models.BooleanField(default=True, verbose_name="Présence de la reine")),
                ("nombre_abeilles", models.PositiveIntegerField(verbose_name="Nombre d'abeilles")),
                (
                    "etat_predit",
                    models.CharField(
                        choices=[
                            ("Bon", "Bon"),
                            ("A_Surveiller", "À surveiller"),
                            ("Risque_Eleve", "Risque élevé"),
                        ],
                        default="Bon",
                        max_length=20,
                        verbose_name="État prédit",
                    ),
                ),
                ("user_id", models.PositiveIntegerField(blank=True, null=True, verbose_name="ID utilisateur")),
                (
                    "id_environnement",
                    models.PositiveIntegerField(blank=True, null=True, verbose_name="ID environnement"),
                ),
            ],
            options={
                "verbose_name": "Ruche",
                "verbose_name_plural": "Ruches",
                "db_table": "ruche",
                "ordering": ["code_ruche"],
            },
        ),
    ]
