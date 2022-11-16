from datetime import datetime, date
from uuid import UUID
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class UUIDMixin(BaseModel):
    id: UUID


class Person(UUIDMixin):
    name: str = Field(max_length=255)


class PersonRoles(str, Enum):
    actor = "actor"
    director = "director"
    producer = "producer"
    writer = "writer"


class FilmWork(UUIDMixin):
    title: str = Field(max_length=255)
    imdb_rating: Optional[float] = Field(None, gte=0, lte=100)
    genre: List[str]
    description: Optional[str] = ""
    director: List[str] = []
    actors_names: List[str] = []
    writers_names: List[str] = []
    actors: List[Person] = []
