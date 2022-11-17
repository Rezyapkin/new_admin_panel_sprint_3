"""
ETL-script for loads data from postgres to elastic search.
!!! Уважаемый ревьюер, большая просьба прочесть файл документации. Мне кажется я запутанный код написал(((
"""

import logging
from datetime import datetime
from time import sleep
from pathlib import Path
from typing import Generator, Any
from json import load

from psutil import process_iter, Process
from elasticsearch import ConnectionError, RequestError
from psycopg2 import Error as PgError
from psycopg2.extensions import connection as pg_connection
from redis.exceptions import RedisError

import data_transform
from config.models import Settings, EtlSettings
from config import settings
from db_connection import postgres_db_connection, redis_db_connection, elastic_search_connection
from decorators import coroutine, repeat_request, backoff
from es_load import MoviesESLoad
from pg_extract import PostgresSQLExtract
from states import State, RedisStorage


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

    @repeat_request(ConnectionError)
    @backoff()
    def check_and_create_index(self, etl: EtlSettings):
        """If the ElasticSearch index does not exist, create it from a json file."""
        elastic_conn = self.elastic_loader.get_elastic()
        if not elastic_conn.indices.exists(index=etl.elastic_index):
            with open(Path.joinpath(Path(settings.config_dir), etl.mapping_file), "r") as fp:
                data = load(fp)
                elastic_conn.indices.create(index=etl.elastic_index, **data)

    @repeat_request(PgError)
    def set_pg_conn(self):
        """The connection to postgresql is managed inside the class."""
        self.pg_conn = postgres_db_connection(self.settings.postgres_dsn, self.settings.db_timeout)

    @repeat_request(RedisError)
    def get_state(self, key, default: Any | None = None) -> Any:
        """Retrieves the state from the storage."""
        return self.state.get_state(key, default)

    @repeat_request(RedisError)
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
        else:
            return "{}_{}_{}".format(index_name, track_field, postfix)

    @staticmethod
    def get_data_transform_class(etl: EtlSettings) -> data_transform.DataTransform:
        """Get a class for transforming data from the application configuration."""
        return getattr(data_transform, etl.transform_class)

    @repeat_request(ConnectionError)
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
        while True:
            etl: EtlSettings = yield
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


def main() -> None:
    redis_adapter = redis_db_connection(settings.redis_host, settings.redis_port, settings.redis_etl_db,
                                        settings.redis_password, connect_timeout=settings.db_timeout)
    elastic_adapter = elastic_search_connection(settings.es_host, settings.es_port, settings.db_timeout)
    ProcessETL(settings, State(RedisStorage(redis_adapter)), MoviesESLoad(elastic_adapter)).start()


# Check running same process.
def started_same_process() -> bool:
    """Checks if a python script with the same name is running."""
    current_process = Process()
    script_name = Path(__file__).name
    find_same_process = False
    for process in process_iter(["pid", "name", "cmdline"]):
        """
        Of course, it was possible to simply compare the cmdline of the process and current_process.
        But the script can be run with or without specifying the path to it.
        """
        if process.name() == current_process.name() and process.pid != current_process.pid:
            for cmdline in current_process.cmdline():
                if cmdline.endswith(script_name):
                    find_same_process = True
                    break
    return find_same_process


if __name__ == "__main__":
    if started_same_process():
        print("The process has already been started")
    else:
        main()
