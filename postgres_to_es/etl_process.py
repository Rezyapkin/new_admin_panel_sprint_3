from datetime import datetime
from time import sleep
from pathlib import Path
from typing import Generator, Any

from psutil import process_iter, Process
from psycopg2 import Error as PgError
from redis.exceptions import RedisError

import etl_data_transform
from config.models import Settings, EtlSettings
from config import settings
from db_connection import postgres_db_connection, redis_db_connection
from decorators import coroutine, repeat_request
from pg_extract import PostgresSQLExtract
from states import State, RedisStorage


class ProcessETL:
    pg_conn = None

    def __init__(self, setting: Settings, state: State):
        self.settings = setting
        self.state = state
        self.set_pg_conn()

    @repeat_request(PgError)
    def set_pg_conn(self):
        self.pg_conn = postgres_db_connection(self.settings.postgres_dsn,
                                              connect_timeout=self.settings.db_timeout)

    @repeat_request(RedisError)
    def get_state(self, key) -> Any:
        return self.state.get_state(key)

    @repeat_request(RedisError)
    def set_state(self, key, value) -> None:
        if isinstance(value, datetime):
            value = value.isoformat()
        self.state.set_state(key, value)

    @staticmethod
    def _get_state_name(index_name: str, track_field: str, postfix: str = ""):
        if postfix == "":
            return "___._{}.{}".format(index_name, track_field)
        else:
            return "___._{}.{}.{}".format(index_name, track_field, postfix)

    @staticmethod
    def _get_data_transform_class(etl: EtlSettings) -> etl_data_transform.DataTransform:
        return getattr(etl_data_transform, etl.transform_class)

    @coroutine
    def extract_data(self) -> Generator[None, EtlSettings, None]:
        while True:
            etl: EtlSettings = yield
            transform_class = self._get_data_transform_class(etl)()
            pg_loader = PostgresSQLExtract(self.pg_conn, etl, self.settings.etl_settings.sql_db)
            for tracked_field in pg_loader.tracked_fields:
                tracked_field_state_name = self._get_state_name(etl.elastic_index, tracked_field, "value")
                offset_state_name = self._get_state_name(etl.elastic_index, tracked_field, "offset")

                tracked_field_start = self.get_state(tracked_field_state_name)

                offset = self.get_state(offset_state_name)
                if offset is None:
                    offset = 0

                for data, state_value, state_offset in pg_loader.extract_data(tracked_field,
                                                                              tracked_field_start, offset):
                    transform_data = transform_class.transform(data)
                    self.set_state(tracked_field_state_name, state_value)
                    self.set_state(offset_state_name, state_offset)

            sleep(self.settings.pause_between_repeated_requests)

    def start(self):
        while True:
            for etl in self.settings.etl_settings.bindings_elastic_to_sql:
                self.extract_data().send(etl)


def main() -> None:

    redis_adapter = redis_db_connection(settings.redis_host, settings.redis_port, settings.redis_etl_db,
                                        settings.redis_password, connect_timeout=settings.db_timeout)

    ProcessETL(settings, State(RedisStorage(redis_adapter))).start()


# Check running same process.
def started_same_process() -> bool:
    current_process = Process()
    script_name = Path(__file__).name
    find_same_process = False
    for process in process_iter(["pid", "name", "cmdline"]):
        '''
        Of course, it was possible to simply compare the cmdline of the process and current_process.
        But the script can be run with or without specifying the path to it.
        '''
        if process.name() == current_process.name() and process.pid != current_process.pid:
            for cmdline in current_process.cmdline():
                if cmdline.endswith(script_name):
                    find_same_process = True
                    break
    return find_same_process


if __name__ == "__main__":
    if not started_same_process():
        print("The process has already been started")
    else:
        main()
