"""A module for transforming data from Postgresql to ElasticSearch."""
from abc import ABC, abstractmethod

from psycopg2.extras import DictRow

from models import FilmWork, PersonRoles, Person, ElasticModel


class DataTransform(ABC):
    @abstractmethod
    def transform(self, data: list[DictRow]) -> ElasticModel:
        pass


class MoviesDataTransform(DataTransform):
    """
    The flexible configuration of PostgresSQLExtract allows you to write a minimum of code in the
    MoviesDataTransform class, designed to transform data from DictRow into a Pydantic model.
    """
    @staticmethod
    def fill_role_persons(record: DictRow, record_transform: FilmWork):
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
            self.fill_role_persons(record, record_transform)
            data_transform.append(record_transform)
        return data_transform
