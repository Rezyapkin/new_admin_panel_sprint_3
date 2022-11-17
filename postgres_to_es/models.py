"""Data models to upload to Elasticsearch."""
from uuid import UUID
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConstrainedList, validator


class UUIDMixin(BaseModel):
    id: UUID = Field()


class ElasticModel(UUIDMixin):
    id_: UUID | None = Field(None, alias="_id")

    @validator("id_", pre=True, always=True)
    def passwords_match(cls, v: UUID | None, values: dict[str, Any], **kwargs) -> Any:
        return values["id"]


class Person(UUIDMixin):
    name: str = Field(max_length=255)


class PersonRoles(str, Enum):
    actor = "actor"
    director = "director"
    producer = "producer"
    writer = "writer"


class FilmWork(ElasticModel):
    title: str = Field(max_length=255)
    imdb_rating: Optional[float] = Field(None, gte=0, lte=100)
    genre: list[str]
    description: Optional[str] = ""
    director: list[str] = []
    actors_names: list[str] = []
    writers_names: list[str] = []
    actors: list[Person] = []
