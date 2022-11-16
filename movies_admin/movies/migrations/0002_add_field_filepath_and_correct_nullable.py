# Generated by Django 4.1.2 on 2022-10-19 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="filmwork",
            name="file_path",
            field=models.URLField(blank=True, null=True, verbose_name="movies url"),
        ),
        migrations.AlterField(
            model_name="filmwork",
            name="creation_date",
            field=models.DateField(null=True, verbose_name="creation date"),
        ),
        migrations.AlterField(
            model_name="filmwork",
            name="description",
            field=models.TextField(null=True, verbose_name="description"),
        ),
        migrations.AlterField(
            model_name="genre",
            name="description",
            field=models.TextField(null=True, verbose_name="description"),
        ),
        migrations.AlterField(
            model_name="personfilmwork",
            name="role",
            field=models.CharField(
                choices=[
                    ("actor", "actor"),
                    ("director", "director"),
                    ("producer", "producer"),
                    ("writer", "writer"),
                ],
                max_length=20,
                verbose_name="role",
            ),
        ),
    ]
