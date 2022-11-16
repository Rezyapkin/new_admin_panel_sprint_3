import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class TimeStampedMixin(models.Model):
    created = models.DateTimeField(_("created"), auto_now_add=True)
    modified = models.DateTimeField(_("modified"), auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class FilmWork(UUIDMixin, TimeStampedMixin):
    class Types(models.TextChoices):
        MOVIE = "movie", _("movie")
        TV_SHOW = "tv_show", _("TV show")

    title = models.CharField(_("title"), max_length=255)
    file_path = models.URLField(_("movies url"), blank=True, null=True)
    description = models.TextField(_("description"), blank=True, null=True)
    creation_date = models.DateField(_("creation date"), null=True)
    rating = models.FloatField(
        _("rating"),
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    type = models.CharField(_("type"), max_length=20, choices=Types.choices)
    genres = models.ManyToManyField(
        "Genre", through="GenreFilmWork", verbose_name=_("genre")
    )
    persons = models.ManyToManyField(
        "Person", through="PersonFilmWork", verbose_name=_("person")
    )

    def __str__(self):
        return "{} ({})".format(self.title, self.get_type_display())

    class Meta:
        db_table = "content\".\"film_work"
        verbose_name = _("Movie")
        verbose_name_plural = _("Movies")
        indexes = [
            models.Index(fields=["creation_date"], name="film_work_creation_date_idx"),
            models.Index(fields=["rating"], name="film_work_rating_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(modified__gt=models.F('creation_date')),
                name='check_start_date',
            ),
        ]


class Genre(UUIDMixin, TimeStampedMixin):
    name = models.CharField(_("title"), unique=True, max_length=255)
    description = models.TextField(_("description"), blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "content\".\"genre"
        verbose_name = _("Genre")
        verbose_name_plural = _("Genres")


class Person(UUIDMixin, TimeStampedMixin):
    full_name = models.CharField(_("full_name"), max_length=255)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = "content\".\"person"
        verbose_name = _("Person")
        verbose_name_plural = _("Persons")


class GenreFilmWork(UUIDMixin):
    film_work = models.ForeignKey(
        "FilmWork", on_delete=models.CASCADE, verbose_name=_("filmwork")
    )
    genre = models.ForeignKey("Genre", on_delete=models.CASCADE, verbose_name=_("genre"))
    created = models.DateTimeField(_("created"), auto_now_add=True)

    def __str__(self):
        return "{} - {}".format(self.film_work, self.genre)

    class Meta:
        db_table = "content\".\"genre_film_work"
        verbose_name = _("Genres movie")
        verbose_name_plural = _("Genres movies")
        constraints = [
            models.UniqueConstraint(fields=("film_work_id", "genre_id"), name="genre_film_work_idx")
        ]


class PersonFilmWork(UUIDMixin):
    class Roles(models.TextChoices):
        ACTOR = "actor", _("actor")
        DIRECTOR = "director", _("director")
        PRODUCER = "producer", _("producer")
        WRITER = "writer", _("writer")

    film_work = models.ForeignKey(
        "FilmWork", on_delete=models.CASCADE, verbose_name=_("film")
    )
    person = models.ForeignKey(
        "Person", on_delete=models.CASCADE, verbose_name=_("person")
    )
    role = models.CharField(_("role"), max_length=20, choices=Roles.choices)
    created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("created")
    )

    def __str__(self):
        return "{} - {}".format(self.film_work, self.person)

    class Meta:
        db_table = "content\".\"person_film_work"
        verbose_name = _("Film persons")
        verbose_name_plural = _("Films persons")
        constraints = [
            models.UniqueConstraint(fields=("film_work_id", "person_id", "role"), name="film_work_person_idx")
        ]
