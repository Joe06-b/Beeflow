from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Stock", "0002_stock_validations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stock",
            name="produit",
            field=models.CharField(
                choices=[
                    ("miel", "Miel"),
                    ("cire", "Cire"),
                    ("pollen", "Pollen"),
                    ("propolis", "Propolis"),
                    ("gelee_royale", "Gelée royale"),
                ],
                max_length=30,
            ),
        ),
    ]
