"""
ETL-script for loads data from postgres to elastic search.
"""

import logging
from datetime import datetime
from time import sleep
from pathlib import Path
from typing import Generator, Any
from json import load

from elasticsearch import ConnectionError
from psycopg2 import Error as PgError
from psycopg2.extensions import connection as pg_connection
from redis.exceptions import RedisError

import data_transform
from config.models import Settings, EtlSettings
from db_connection import postgres_db_connection
from decorators import coroutine, backoff
from es_load import MoviesESLoad
from pg_extract import PostgresSQLExtract
from states import State


class ProcessETL:
    """
    The class manages the launch of internal components: extracts, transforms, loads data
    """
    pg_conn: pg_connection | None = None

    def __init__(self, setting: Settings, state: State, elastic_loader: MoviesESLoad):
        self.settings = setting
        self.state = state
        self.elastic_loader = elastic_loader
        self.set_pg_conn()

    @backoff()
    def check_and_create_index(self, etl: EtlSettings):
        """If the ElasticSearch index does not exist, create it from a json file."""
        elastic_conn = self.elastic_loader.get_elastic()
        if not elastic_conn.indices.exists(index=etl.elastic_index):
            with open(Path.joinpath(Path(self.settings.config_dir), etl.mapping_file), "r") as fp:
                data = load(fp)
                elastic_conn.indices.create(index=etl.elastic_index, **data)

    @backoff()
    def set_pg_conn(self):
        """The connection to postgresql is managed inside the class."""
        self.pg_conn = postgres_db_connection(self.settings.postgres_dsn, self.settings.db_timeout)

    @backoff()
    def get_state(self, key, default: Any | None = None) -> Any:
        """Retrieves the state from the storage."""
        return self.state.get_state(key, default)

    def set_state(self, key, value) -> None:
        """Set the state from the storage."""
        if isinstance(value, datetime):
            value = value.isoformat()
        self.state.set_state(key, value)

    @staticmethod
    def get_state_name(index_name: str, track_field: str, postfix: str = ""):
        """Generates the name of the key for the storage."""
        if postfix == "":
            return "{}_{}".format(index_name, track_field)
        return "{}_{}_{}".format(index_name, track_field, postfix)

    @staticmethod
    def get_data_transform_class(etl: EtlSettings) -> data_transform.DataTransform:
        """Get a class for transforming data from the application configuration."""
        return getattr(data_transform, etl.transform_class)

    @backoff()
    def repeat_load_data(self, index, data):
        self.elastic_loader.load(data, index)

    @coroutine
    def load_data(self) -> Generator[None, tuple[str, list[dict]], None]:
        """A coroutine that loading data into Elasticsearch."""
        while True:
            index, data = yield
            self.repeat_load_data(index, data)

    @coroutine
    def extract_data(self) -> Generator[None, EtlSettings, None]:
        """A coroutine that extracting data from PostgresSQL."""
        while etl := (yield):
            self.check_and_create_index(etl)
            transform_class = self.get_data_transform_class(etl)()
            pg_loader = PostgresSQLExtract(self.pg_conn, etl, self.settings.etl_settings.sql_db)
            for tracked_field in pg_loader.tracked_fields:
                tracked_field_state_name = self.get_state_name(etl.elastic_index, tracked_field, "value")
                offset_state_name = self.get_state_name(etl.elastic_index, tracked_field, "offset")
                tracked_field_start = self.get_state(tracked_field_state_name)
                offset = self.get_state(offset_state_name, 0)
                """Getting data from Postgresql. If a Postgre error occurs, we log and reconnect."""
                while True:
                    try:
                        extracted = pg_loader.extract_data(tracked_field, tracked_field_start, offset)
                        break
                    except PgError as e:
                        logging.log(logging.WARNING, e)
                        # I don't know if I need to close the connection if the base has already fallen.
                        # self.pg_conn.close()
                        self.set_pg_conn()

                for data, state_value, state_offset in extracted:
                    transform_data = transform_class.transform(data)
                    self.load_data().send((etl.elastic_index, transform_data))
                    self.set_state(tracked_field_state_name, state_value)
                    self.set_state(offset_state_name, state_offset)

            logging.log(logging.INFO, "Check all tables. Paused.")
            sleep(self.settings.pause_between_repeated_requests)

    def start(self):
        """Main loop ETL-process."""
        while True:
            for etl in self.settings.etl_settings.bindings_elastic_to_sql:
                self.extract_data().send(etl)
