from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="financialevent",
            index=models.Index(
                fields=["year", "month"],
                name="financialevent_year_month_idx",
            ),
        ),
    ]
