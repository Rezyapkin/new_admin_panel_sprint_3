from typing import Dict, List, Tuple, Any

from psycopg2.extensions import connection as _connection
from psycopg2.extras import DictCursor, DictRow

from config.models import ExchangeTableSettings, SQLDBSettings


class QueryBuildMixin:
    TRACKED_FIELD_NAME = "_tracked_field"
    TRACKED_TABLE_NAME = "_tracked_table"

    def __init__(self, source: ExchangeTableSettings, db_settings: SQLDBSettings | None = None):
        self.source = source
        self.db_schema = "" if db_settings is None else db_settings.db_schema
        self.query_limit = None if db_settings is None else db_settings.query_entries_limit
        self.default_key_field = "id" if db_settings is None else db_settings.key_field_name

    @staticmethod
    def _get_table_alias(table: ExchangeTableSettings) -> str:
        return format(table.name if not table.alias else table.alias)

    @staticmethod
    def _get_full_field_name(table_alias: str, field: str, quotes: bool = True) -> str:
        return "\"{0}\".\"{1}\"".format(table_alias, field) if quotes else "{0}.{1}".format(table_alias, field)

    @staticmethod
    def _get_field_alias(table: ExchangeTableSettings, field: str):
        table_alias = PostgresSQLLoader._get_table_alias(table)
        return table.aliases.get(field, "{0}__{1}".format(table_alias, field))

    def _get_full_table_name(self, table: ExchangeTableSettings) -> str:
        db_schema = table.db_schema if table.db_schema else self.db_schema
        table_name = table.name if not db_schema else "\"{}\".\"{}\"".format(db_schema, table.name)
        return "{} AS \"{}\"".format(table_name, self._get_table_alias(table))

    def _get_table_with_joins(self, table: ExchangeTableSettings, parent_table: ExchangeTableSettings):
        table_alias = self._get_table_alias(table)
        joins = None
        if parent_table is not None and len(table.join) > 0:
            parent_table_alias = self._get_table_alias(parent_table)
            joins = [
                "{} = {}".format(self._get_full_field_name(parent_table_alias, value),
                                 self._get_full_field_name(table_alias, key))
                for key, value in table.join.items()
            ]
        return self._get_full_table_name(table), joins

    def _get_table_key_field_name(self, table: ExchangeTableSettings):
        return table.key_field_name or self.default_key_field

    def _get_fields_and_tables_parts_sql(self, current_table: ExchangeTableSettings,
                                         parent_table: ExchangeTableSettings | None = None,
                                         depth=0) -> Dict[str, List | Tuple]:
        result = {
            "fields": [],  # [(field, field_full_name, field_alias)]
            "tables": []  # [(table_with_alias, join_on)]
        }
        table_alias = self._get_table_alias(current_table)

        # Adding fields to result
        for field in current_table.fields:
            field_alias = self._get_field_alias(current_table, field)
            if parent_table is None:
                field_alias = current_table.aliases.get(field, field)
            field_full_name = self._get_full_field_name(table_alias, field)
            result["fields"].append((field, field_full_name, field_alias))

        # Adding current table to result
        result["tables"].append(self._get_table_with_joins(current_table, parent_table))

        # Max depth for children table = 2
        if current_table.children is not None and depth < 2:
            for children_table in current_table.children:
                children_result = self._get_fields_and_tables_parts_sql(children_table, current_table, depth + 1)
                for key, value in children_result.items():
                    result[key] += value

        # Grouping fields
        if depth == 1 and current_table.group is not None:
            if len(result["fields"]) == 1:
                field = result["fields"][0]
                agg = "array_agg (DISTINCT {})".format(field[1])
                result["fields"][0] = (None, agg, current_table.group)
            elif len(result["fields"]) > 1:
                fields = ", \n".join(["  '{}', {}".format(field[0] if "__" in field[2] else field[2], field[1])
                                      for field in result["fields"]])
                agg = "COALESCE (json_agg(DISTINCT jsonb_build_object(\n{}\n))" \
                      " FILTER (WHERE {} is not null), '[]')".format(fields, result["fields"][-1][1])
                result["fields"] = [(None, agg, current_table.group)]
        return result

    def _get_tracked_fields_with_related_tables(self, current_table: ExchangeTableSettings,
                                                parent_tables: List[ExchangeTableSettings] | None = None,
                                                depth=0):
        result = {}  # tracked_field: [(table_with_alias, join_on), ...]
        if parent_tables is None:
            parent_tables = [current_table]
        else:
            parent_tables.append(current_table)
        if current_table.field_actual_state_name:
            field_full_name = self._get_full_field_name(self._get_table_alias(current_table),
                                                        current_table.field_actual_state_name, False)

            first_table = parent_tables[0]
            key_field = self._get_table_key_field_name(first_table)
            key_field_full_name = self._get_full_field_name(self._get_table_alias(first_table), key_field)
            query_str_list = [
                "JOIN (\n  SELECT {0} AS \"id\", {1} AS \"{2}\"".format(key_field_full_name, field_full_name,
                                                                        self.TRACKED_FIELD_NAME),
            ]
            parent_table = None
            for table in parent_tables:
                table_str = "  FROM" if parent_table is None else "  JOIN"
                table_join = self._get_table_with_joins(table, parent_table)
                if table_join[1] is not None:
                    query_str_list.append("{0} {1} ON {2}".format(table_str, table_join[0], ", ".join(table_join[1])))
                else:
                    query_str_list.append("{0} {1}".format(table_str, table_join[0]))
                parent_table = table

            query_str_list.append("  WHERE {0} > %s \n  ORDER BY {0}".format(field_full_name))
            if self.query_limit is not None:
                query_str_list.append("  LIMIT {} OFFSET %s".format(self.query_limit))
            query_str_list.append("  ) AS \"{0}\" ON {1} = \"{0}\".\"id\"".format(self.TRACKED_TABLE_NAME,
                                                                                      key_field_full_name))
            result[field_full_name] = "\n".join(query_str_list)

        if current_table.children is not None and depth < 2:
            for children_table in current_table.children:
                child_result = self._get_tracked_fields_with_related_tables(children_table, parent_tables, depth + 1)
                result.update(child_result)

        parent_tables.pop()
        return result

    def get_tracked_fields_with_query(self):
        return self._get_tracked_fields_with_related_tables(self.source.table)

    def select_query_for_load(self, where_filter: str = "", adding_fields: [str] = [], adding_join: [str] = []) -> str:
        fields_and_tables = self._get_fields_and_tables_parts_sql(self.source.table)
        tables = []
        for table in fields_and_tables["tables"]:
            tables.append(table[0] if table[1] is None else "LEFT JOIN {} ON {}".format(table[0], ", ".join(table[1])))
        tables.extend(adding_join)
        fields = []
        group_by = []
        group_by_need = False
        for field in fields_and_tables["fields"]:
            if field[0] is not None:
                group_by.append(field[1])
            else:
                group_by_need = True
            fields.append("{} AS \"{}\"".format(field[1], field[2]))
        fields.extend(adding_fields)
        group_by.extend(adding_fields)
        fields_str = ",\n ".join(fields)
        tables_str = "\n".join(tables)
        group_by_str = ""
        if group_by_need:
            group_by_str = "GROUP BY\n {}".format(",\n ".join(group_by))
        where_str = "" if where_filter == "" else "\nWHERE {}".format(where_filter)
        sql_text = "SELECT \n {0} \nFROM {1} {2}\n{3}\n".format(fields_str, tables_str, where_str, group_by_str)

        if self.query_limit is not None:
            sql_text += "LIMIT {}".format(self.query_limit)

        return sql_text


class PostgresSQLLoader(QueryBuildMixin):
    def __init__(self, conn: _connection, source: ExchangeTableSettings, db_settings: SQLDBSettings | None = None,
                 batch_size: int = 1000):
        self.conn = conn
        self.batch_size = batch_size
        QueryBuildMixin.__init__(self, source, db_settings)
        self.tracked_fields = self.get_tracked_fields_with_query()

    def _get_query_for_tracked_field(self, tracked_field):
        adding_fields = ["\"{0}\".\"{1}\"".format(self.TRACKED_TABLE_NAME, self.TRACKED_FIELD_NAME)]
        adding_join = [self.tracked_fields[tracked_field]]
        return self.select_query_for_load(adding_fields=adding_fields, adding_join=adding_join)

    def _get_checked_field_info(self, data: List[DictRow], tracked_field_state_value: Any):
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

    def load_data(self, tracked_field: str, tracked_field_state_value: Any,
                  tracked_field_state_offset: int = 0) -> dict:
        sql_text = self._get_query_for_tracked_field(tracked_field)
        print(sql_text)
        cur = self.conn.cursor(cursor_factory=DictCursor)
        cur.execute(sql_text, (tracked_field_state_value, tracked_field_state_offset))
        while data := cur.fetchmany(size=self.batch_size):
            if len(data) == 0:
                tracked_field_state = (tracked_field_state_value, tracked_field_state_offset)
            elif len(data) < self.batch_size:
                tracked_field_state = (data[-1][self.TRACKED_FIELD_NAME], 0)
            else:
                tracked_field_state = self._get_checked_field_info(data, tracked_field_state_value)
            yield data, *tracked_field_state
        cur.close()
