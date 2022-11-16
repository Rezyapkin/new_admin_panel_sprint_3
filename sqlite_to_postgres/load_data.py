"""Script for loads data from sqlite to postgres."""
from contextlib import contextmanager
import logging
import sqlite3

import psycopg2
from psycopg2.extensions import connection as _connection
from psycopg2.extras import DictCursor, register_uuid

import models
from config import settings
from db_exchange import PostgresSaver, SQLiteExtractor


@contextmanager
def conn_context(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def load_from_sqlite(connection: sqlite3.Connection, pgconn: _connection, count_entries, default_key_name):
    postgres_saver = PostgresSaver(pgconn, settings.get("schema_dest_db", ""))
    sqlite_extractor = SQLiteExtractor(connection, count_entries)
    for table in settings.tables:
        model = getattr(models, table.model_name)
        key_fields = table.get("key_fields", default=[default_key_name])
        try:
            data = sqlite_extractor.extract(table.name, model, table.fields)
            for part_data in data:
                postgres_saver.save(table.name, model, part_data, key_fields)
        except sqlite3.Error as e:
            logging.error("Read table \"{}\": {}".format(table.model_name, e))
        except psycopg2.Error as e:
            logging.error("Write table \"{}\": {}".format(table.model_name, e))


if __name__ == "__main__":
    sqlite_path = settings.sqlite_db_path
    with (conn_context(sqlite_path) as sqlite_conn,
          psycopg2.connect(**settings.pg_dsl, cursor_factory=DictCursor) as pgconn):
        register_uuid()
        load_from_sqlite(sqlite_conn, pgconn, settings.count_entries, settings.get("key_field_name"))
