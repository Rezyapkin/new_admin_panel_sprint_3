"""Check consistency of SQLite source and PostreSQL destination."""
import sqlite3
from os import path
from datetime import datetime

import pytest
import psycopg2
from psycopg2.extensions import connection as pg_connection

from ..config import settings


def convert_timestamp_with_time_zone(val):
    """Converts a string to a datetime"""
    str_date = val.decode("UTF-8")
    str_date_split = str_date.split(".")
    if len(str_date_split[1]) < 10:
        str_date_split[1] += "00"
    for zone_splitter in ["+", "-"]:
        str_date_split[1] = str_date_split[1].replace(zone_splitter, " " + zone_splitter)
    return datetime.strptime(".".join(str_date_split), "%Y-%m-%d %H:%M:%S.%f %z")


@pytest.fixture(scope="session")
def sqlite_connect() -> sqlite3.Connection:
    """A fixture that establishes a connection to SQLite DB."""
    conn = sqlite3.connect(path.join(settings.app_dir, settings.sqlite_db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    sqlite3.register_converter("timestamp", convert_timestamp_with_time_zone)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def pg_connect() -> pg_connection:
    """A fixture that establishes a connection to PostgresSQL DB."""
    conn = psycopg2.connect(**settings.pg_dsl)
    yield conn
    conn.close()


def get_select_query_text(fields: [str], table_name: str, order_fields: [] = []) -> str:
    """Get SQL select query for table 'table_name' with fields.
    Args:
        fields: table fields involved in the sql query
        table_name: table name
        order_fields: fields by which sorting will be performed

    Returns:
        Text SQL select query.
    """
    str_fields = ", ".join(["\"{0}\"".format(field) for field in fields])
    sql = "SELECT DISTINCT {0} \nFROM {1}".format(str_fields, table_name)
    if order_fields:
        str_orders = ", ".join(["\"{0}\"".format(field) for field in order_fields])
        sql += "\nORDER BY {0};".format(str_orders)
    return sql


@pytest.mark.parametrize("table_name, table_copy_settings",
                         [pytest.param(table.name, table) for table in settings.tables])
def test_similarity_table(sqlite_connect: sqlite3.Connection, pg_connect: pg_connection,
                          table_name: str, table_copy_settings: dict):
    """The test verifies the contents of the tables specified in the application settings."""
    print(table_name)
    sqlite_cur = sqlite_connect.cursor()
    pg_cur = pg_connect.cursor()
    fields = table_copy_settings.fields
    if table_copy_settings.get("key_fields"):
        # For tables that are binders for many-to-many, we exclude the id from the query.
        fields.remove(settings.key_field_name)
    key_fields = table_copy_settings.get("key_fields", default=[settings.key_field_name])
    sqlite_sql = get_select_query_text(fields, table_name, key_fields)
    if "aliases" in table_copy_settings:
        # If aliases are set for the fields, then you need to get a new list of fields for PostgresSQL.
        pg_fields = [table_copy_settings.aliases.get(field, default=field) for field in fields]
    else:
        pg_fields = fields
    pg_sql = get_select_query_text(pg_fields, "\"{0}\".\"{1}\"".format(settings.schema_dest_db, table_name), key_fields)

    sqlite_cur.execute(sqlite_sql)
    pg_cur.execute(pg_sql)
    while sqlite_records := sqlite_cur.fetchmany(settings.count_entries):
        pg_records = pg_cur.fetchmany(settings.count_entries)
        assert len(sqlite_records) == len(pg_records)
        assert sqlite_records == pg_records
