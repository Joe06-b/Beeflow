"""
Intégration avec rucheapp : le champ statique id_ruche (choix R-001 ... R-005)
devient une vraie clé étrangère `ruche` vers rucheapp.Ruche.

La colonne en base garde son nom "id_ruche" (db_column), donc aucune donnée n'est perdue.

Les suivis déjà enregistrés qui pointent vers une ruche statique sont rattachés :
  1. à la vraie ruche qui porte le même code (ex : "R-002"), si elle existe ;
  2. sinon à la ruche qui a le même numéro, si elle existe ;
  3. sinon une ruche est créée avec l'ancien code, pour ne perdre aucun suivi
     (ses informations pourront être complétées ensuite dans Gestion des ruches).
"""
import uuid
from datetime import date

import django.db.models.deletion
from django.db import migrations, models

ANCIENS_CODES = {1: "R-001", 2: "R-002", 3: "R-003", 4: "R-004", 5: "R-005"}


def rattacher_suivis_aux_ruches(apps, schema_editor):
    Suivi = apps.get_model("SuiviSanitaireApp", "SuiviSanitaire")
    Ruche = apps.get_model("rucheapp", "Ruche")

    # Regrouper d'abord les suivis par ancien numéro de ruche (avant toute modification)
    groupes = {}
    for id_suivi, ancien_id in Suivi.objects.values_list("id_suivi", "id_ruche"):
        groupes.setdefault(ancien_id, []).append(id_suivi)

    for ancien_id, ids_suivis in groupes.items():
        code = ANCIENS_CODES.get(ancien_id, f"R-{ancien_id:03d}")

        ruche = Ruche.objects.filter(code_ruche=code).first()
        if ruche is None and ancien_id not in ANCIENS_CODES:
            ruche = Ruche.objects.filter(pk=ancien_id).first()
        if ruche is None:
            code_libre, n = code, 1
            while Ruche.objects.filter(code_ruche=code_libre).exists():
                n += 1
                code_libre = f"{code}-{n}"
            ruche = Ruche.objects.create(
                qr_token=uuid.uuid4(),
                code_ruche=code_libre,
                type_ruche="Autre",
                race_abeilles="Autre",
                date_installation=date.today(),
                presence_reine=True,
                nombre_abeilles=1,
                etat_predit="Bon",
            )

        if ruche.pk != ancien_id:
            Suivi.objects.filter(id_suivi__in=ids_suivis).update(id_ruche=ruche.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("SuiviSanitaireApp", "0001_initial"),
        ("rucheapp", "0004_ruche_qr_token"),
    ]

    operations = [
        # 1. Rattacher les anciens suivis à de vraies ruches (le champ est encore un entier)
        migrations.RunPython(rattacher_suivis_aux_ruches, migrations.RunPython.noop),
        # 2. Renommer le champ Python id_ruche -> ruche
        migrations.RenameField(
            model_name="suivisanitaire",
            old_name="id_ruche",
            new_name="ruche",
        ),
        # 3. En faire une clé étrangère (colonne "id_ruche" en base)
        migrations.AlterField(
            model_name="suivisanitaire",
            name="ruche",
            field=models.ForeignKey(
                db_column="id_ruche",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="suivis",
                to="rucheapp.ruche",
                verbose_name="Ruche",
            ),
        ),
    ]
