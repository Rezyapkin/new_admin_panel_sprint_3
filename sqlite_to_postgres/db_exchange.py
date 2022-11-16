"""A module that implements functionality for downloading and uploading data from a DB."""
from typing import Callable
from sqlite3 import Connection as SqliteConnection
from sqlite3 import Cursor

from psycopg2.extensions import connection as psql_connection
from psycopg2.extras import execute_values
from pydantic import BaseModel

import query_build


class PostgresSaver:
    """Class for saving data to PostgresSQL."""
    def __init__(self, conn: psql_connection, schema: str = ""):
        self.conn = conn
        self.schema = schema

    def _full_table_name(self, table_name: str) -> str:
        """Get table fullname by scheme and table name."""
        if self.schema == "":
            return "\"{}\"".format(table_name)
        else:
            return "\"{0}\".\"{1}\"".format(self.schema, table_name)

    def save(self, table_name: str, model: BaseModel, data: list[BaseModel], key_fields: []):
        """Save data in PostgresSQL.

        Args:
            table_name: table name
            model: data model Pydantic
            data: list of records Pydantic
            key_fields: List of field names to be used in the instruction ON CONFLICT
        """
        cur = self.conn.cursor()
        full_table_name = self._full_table_name(table_name)
        sql = query_build.get_insert_query_for_model_text(model, full_table_name, key_fields)
        execute_values(cur, sql, [item.dict() for item in data], template=query_build.get_template_insert_model(model))
        cur.close()
        self.conn.commit()


class SQLiteExtractor:
    """Class for extracting data from SQLite."""
    def __init__(self, conn: SqliteConnection, count_read_entries=1):
        """Init the PostgresSaver object.
        Args:
            conn: connection to PostgresSQL database
            count_read_entries: the number of table entries that are read at a time
        """
        self.conn = conn
        self.count_read_entries = count_read_entries

    @staticmethod
    def model_factory(model) -> Callable:
        """The closure is returned by row_factory for a specific Pydantic model"""
        def factory(cursor: Cursor, row: tuple) -> BaseModel:
            col_names = [col[0] for col in cursor.description]
            return model.parse_obj({key: value for key, value in zip(col_names, row)})

        return factory

    def extract(self, table_name: str, model: BaseModel, fields: [str]) -> list[BaseModel]:
        """Extracts data from the SQLite table in chunks.

        Args:
            table_name: table name
            model: data model Pydantic
            fields: list table fields

        Yields:
            A list with no more than count_read_entries-entries containing table entries in the Pydantic Model
        """
        self.conn.row_factory = self.model_factory(model)
        cur = self.conn.cursor()
        cur.execute(query_build.get_select_query_text(fields, table_name))
        while data := cur.fetchmany(size=self.count_read_entries):
            yield data
        cur.close()
