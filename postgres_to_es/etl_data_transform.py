from abc import ABC, abstractmethod

from psycopg2.extras import DictRow
from pydantic import BaseModel

from models import FilmWork, PersonRoles, Person


class DataTransform(ABC):
    @abstractmethod
    def transform(self, data: list[DictRow]) -> BaseModel:
        pass


class MoviesDataTransform(DataTransform):
    @staticmethod
    def _fill_role_persons(record: DictRow, record_transform: FilmWork):
        role_filters = {
            PersonRoles.director: "director",
            PersonRoles.actor: "actors_names",
            PersonRoles.writer: "writers_names",
        }
        for person in record["persons"]:
            if person["role"] in role_filters:
                getattr(record_transform, role_filters[person["role"]]).append(person["name"])
            if person["role"] == PersonRoles.actor:
                record_transform.actors.append(Person.parse_obj(person))

    def transform(self, data: list[DictRow]) -> list[FilmWork]:
        data_transform = []
        for record in data:
            record_transform = FilmWork.parse_obj(record)
            self._fill_role_persons(record, record_transform)
            data_transform.append(record_transform)
        return data_transform
