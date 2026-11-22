from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("Stock", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="stock",
            constraint=models.CheckConstraint(
                condition=Q(capacite_max__gt=0),
                name="stock_capacite_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="stock",
            constraint=models.CheckConstraint(
                condition=Q(quantite__gte=0),
                name="stock_quantite_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="stock",
            constraint=models.CheckConstraint(
                condition=Q(seuil_alerte__gte=0),
                name="stock_seuil_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="stock",
            constraint=models.CheckConstraint(
                condition=Q(quantite__lte=F("capacite_max")),
                name="stock_quantite_within_capacity",
            ),
        ),
        migrations.AddConstraint(
            model_name="stock",
            constraint=models.CheckConstraint(
                condition=Q(seuil_alerte__lte=F("capacite_max")),
                name="stock_seuil_within_capacity",
            ),
        ),
    ]
