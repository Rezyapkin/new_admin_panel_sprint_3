# Generated by Django 4.1.2 on 2022-10-18 06:23

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FilmWork",
            fields=[
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    models.DateTimeField(auto_now=True, verbose_name="modified"),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                ("creation_date", models.DateField(verbose_name="creation date")),
                (
                    "rating",
                    models.FloatField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="rating",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("movie", "movie"), ("tv_show", "TV show")],
                        max_length=20,
                        verbose_name="type",
                    ),
                ),
            ],
            options={
                "verbose_name": "Movie",
                "verbose_name_plural": "Movies",
                "db_table": 'content"."film_work',
            },
        ),
        migrations.CreateModel(
            name="Genre",
            fields=[
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    models.DateTimeField(auto_now=True, verbose_name="modified"),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, unique=True, verbose_name="title"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
            ],
            options={
                "verbose_name": "Genre",
                "verbose_name_plural": "Genres",
                "db_table": 'content"."genre',
            },
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    models.DateTimeField(auto_now=True, verbose_name="modified"),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("full_name", models.CharField(max_length=255)),
            ],
            options={
                "verbose_name": "Person",
                "verbose_name_plural": "Persons",
                "db_table": 'content"."person',
            },
        ),
        migrations.CreateModel(
            name="PersonFilmWork",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("actor", "actor"),
                            ("director", "director"),
                            ("producer", "producer"),
                        ],
                        max_length=20,
                        verbose_name="role",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "film_work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="movies.filmwork",
                        verbose_name="film",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="movies.person",
                        verbose_name="person",
                    ),
                ),
            ],
            options={
                "verbose_name": "Film persons",
                "verbose_name_plural": "Films persons",
                "db_table": 'content"."person_film_work',
            },
        ),
        migrations.CreateModel(
            name="GenreFilmWork",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "film_work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="movies.filmwork",
                        verbose_name="filmwork",
                    ),
                ),
                (
                    "genre",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="movies.genre",
                        verbose_name="genre",
                    ),
                ),
            ],
            options={
                "verbose_name": "Genres movie",
                "verbose_name_plural": "Genres movies",
                "db_table": 'content"."genre_film_work',
            },
        ),
        migrations.AddField(
            model_name="filmwork",
            name="genres",
            field=models.ManyToManyField(
                through="movies.GenreFilmWork", to="movies.genre", verbose_name="genre"
            ),
        ),
        migrations.AddField(
            model_name="filmwork",
            name="persons",
            field=models.ManyToManyField(
                through="movies.PersonFilmWork",
                to="movies.person",
                verbose_name="person",
            ),
        ),
        migrations.AddConstraint(
            model_name="personfilmwork",
            constraint=models.UniqueConstraint(
                fields=("film_work_id", "person_id", "role"), name="film_work_person_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="genrefilmwork",
            constraint=models.UniqueConstraint(
                fields=("film_work_id", "genre_id"), name="genre_film_work_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="filmwork",
            index=models.Index(
                fields=["creation_date"], name="film_work_creation_date_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="filmwork",
            index=models.Index(fields=["rating"], name="film_work_rating_idx"),
        ),
        migrations.AddConstraint(
            model_name="filmwork",
            constraint=models.CheckConstraint(
                check=models.Q(("modified__gt", models.F("creation_date"))),
                name="check_start_date",
            ),
        ),
    ]