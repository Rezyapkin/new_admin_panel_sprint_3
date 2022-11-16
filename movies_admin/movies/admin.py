from django.contrib import admin
from .models import FilmWork, Genre, Person, GenreFilmWork, PersonFilmWork


class GenreFilmWorkInline(admin.TabularInline):
    model = GenreFilmWork


class PersonFilmWorkInline(admin.TabularInline):
    model = PersonFilmWork


@admin.register(FilmWork)
class FilmWorkAdmin(admin.ModelAdmin):
    inlines = (GenreFilmWorkInline, PersonFilmWorkInline)
    list_display = ("title", "type", "creation_date", "rating", "created", "modified")
    list_filter = ("type", "rating", "creation_date", "created")
    search_fields = ("title", "description", "id")


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "created", "modified")
    list_filter = ("created", "modified")
    search_fields = ("name", "description", "id")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("full_name", "created", "modified")
    list_filter = ("created", "modified")
    search_fields = ("full_name", "description", "id")
