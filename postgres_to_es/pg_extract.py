"""
A module that extracts data from Postgresql tables.
"""
from typing import Any

from psycopg2.extensions import connection as _connection
from psycopg2.extras import DictCursor, DictRow

from config.models import ExchangeTableSettings, SQLDBSettings
from sql_build import QueryBuildMixin


class PostgresSQLExtract(QueryBuildMixin):
    def __init__(self, conn: _connection, source: ExchangeTableSettings, db_settings: SQLDBSettings | None = None,
                 batch_size: int = 1000):
        self.conn = conn
        self.batch_size = batch_size
        super(QueryBuildMixin).__init__(self, source, db_settings)
        self.tracked_fields = self.get_tracked_fields_with_query()

    def _get_query_for_tracked_field(self, tracked_field):
        adding_fields = ["\"{0}\".\"{1}\"".format(self.TRACKED_TABLE_NAME, self.TRACKED_FIELD_NAME)]
        adding_join = [self.tracked_fields[tracked_field]]
        return self.select_query_for_load(adding_fields=adding_fields, adding_join=adding_join)

    def _get_checked_field_info(self, data: list[DictRow], tracked_field_state_value: Any):
        last_record = data[-1]
        offset = 0
        state_value = tracked_field_state_value
        for record in reversed(data):
            if last_record[self.TRACKED_FIELD_NAME] == record[self.TRACKED_FIELD_NAME]:
                offset += 1
            else:
                state_value = record[self.TRACKED_FIELD_NAME]
                break
        return state_value, offset

    def extract_data(self, tracked_field: str, tracked_field_state_value: Any,
                     tracked_field_state_offset: int = 0) -> tuple[list[DictRow], str, str]:
        """
        Retrieves data from PostgresSQL.

        Args:
            tracked_field: The field that is used to track changes.
                Most often it is modified, updated_at, auto-increment id.
            tracked_field_state_value: The values of the field above whose records were successfully transferred.
            tracked_field_state_offset: When changing a child table, it may happen that the data for
                one modification date affects several tens of thousands of records of the main table.
                The offset field comes to the rescue, which remembers how many records for the value of
                the monitored field have already been read.

        Returns:
            Tuple (A list with data in Dict Row format,
                   a new value of the monitored field that will need to be saved in case of successful
                        data transfer to ElasticSearch,
                   a new offset value)
        """
        sql_text = self._get_query_for_tracked_field(tracked_field)
        if tracked_field_state_value:
            sql_text = sql_text.replace(self.WHERE_COMMENT, "> %s ")
            execute_params = [tracked_field_state_value, tracked_field_state_offset]
        else:
            execute_params = [tracked_field_state_offset]

        # print(sql_text)
        cur = self.conn.cursor(cursor_factory=DictCursor)
        cur.execute(sql_text, execute_params)
        while data := cur.fetchmany(size=self.batch_size):
            if len(data) == 0:
                tracked_field_state = (tracked_field_state_value, tracked_field_state_offset)
            elif len(data) < self.batch_size:
                tracked_field_state = (data[-1][self.TRACKED_FIELD_NAME], 0)
            else:
                tracked_field_state = self._get_checked_field_info(data, tracked_field_state_value)
            yield data, *tracked_field_state
        cur.close()
