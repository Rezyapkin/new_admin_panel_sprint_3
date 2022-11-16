"""Pydantic models for DB tables."""
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CreatedTimeStampedMixin(BaseModel):
    created: datetime = Field(alias="created_at")


class TimeStampedMixin(CreatedTimeStampedMixin):
    modified: datetime = Field(alias="updated_at")


class UUIDMixin(BaseModel):
    id: UUID


class FileWorkTypeEnum(str, Enum):
    movie = "movie"
    tv_show = "TV show"


class FilmWork(UUIDMixin, TimeStampedMixin):
    title: str = Field(max_length=255)
    file_path: Optional[str] = None
    description: Optional[str] = None
    creation_date: Optional[date] = None
    rating: Optional[float] = Field(None, gte=0, lte=100)
    type: FileWorkTypeEnum


class Genre(UUIDMixin, TimeStampedMixin):
    name: str = Field(max_length=255)
    description: Optional[str] = None


class Person(UUIDMixin, TimeStampedMixin):
    full_name: str = Field(max_length=255)


class GenreFilmWork(UUIDMixin, CreatedTimeStampedMixin):
    film_work_id: UUID
    genre_id: UUID


class PersonRoles(str, Enum):
    actor = "actor"
    director = "director"
    producer = "producer"
    writer = "writer"


class PersonFilmWork(UUIDMixin, CreatedTimeStampedMixin):
    film_work_id: UUID
    person_id: UUID
    role: PersonRoles
