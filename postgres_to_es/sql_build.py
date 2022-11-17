"""
A very flexible query constructor (albeit confusing)
that allows you to describe the structure of related tables in a few lines.
For more information, see the application documentation.
"""
from config.models import ExchangeTableSettings, SQLDBSettings


class QueryBuildMixin:
    """The query construction functionality for the PostgresSQL Extractor placed in a separate class."""
    # The name of the SQL service subquery used to sort and filter newly modified data
    TRACKED_FIELD_NAME = "_tracked_field"
    # The name of the service field from the SQL subquery used to sort and filter newly modified data
    TRACKED_TABLE_NAME = "_tracked_table"
    # The crutch is used to get rid of filtering for the first requests.
    WHERE_COMMENT = "IS NOT NULL /*CHANGE*/"

    def __init__(self, source: ExchangeTableSettings, db_settings: SQLDBSettings | None = None):
        self.source = source
        self.db_schema = "" if db_settings is None else db_settings.db_schema
        self.query_limit = None if db_settings is None else db_settings.query_entries_limit
        self.default_key_field = "id" if db_settings is None else db_settings.key_field_name

    @staticmethod
    def get_table_alias(table: ExchangeTableSettings) -> str:
        return format(table.name if not table.alias else table.alias)

    @staticmethod
    def get_full_field_name(table_alias: str, field: str, quotes: bool = True) -> str:
        return "\"{0}\".\"{1}\"".format(table_alias, field) if quotes else "{0}.{1}".format(table_alias, field)

    def get_field_alias(self, table: ExchangeTableSettings, field: str):
        table_alias = self.get_table_alias(table)
        return table.aliases.get(field, "{0}__{1}".format(table_alias, field))

    def get_full_table_name(self, table: ExchangeTableSettings) -> str:
        db_schema = table.db_schema if table.db_schema else self.db_schema
        table_name = table.name if not db_schema else "\"{}\".\"{}\"".format(db_schema, table.name)
        return "{} AS \"{}\"".format(table_name, self.get_table_alias(table))

    def get_table_with_joins(self, table: ExchangeTableSettings, parent_table: ExchangeTableSettings):
        table_alias = self.get_table_alias(table)
        joins = None
        if parent_table is not None and len(table.join) > 0:
            parent_table_alias = self.get_table_alias(parent_table)
            joins = [
                "{} = {}".format(self.get_full_field_name(parent_table_alias, value),
                                 self.get_full_field_name(table_alias, key))
                for key, value in table.join.items()
            ]
        return self.get_full_table_name(table), joins

    def get_table_key_field_name(self, table: ExchangeTableSettings):
        return table.key_field_name or self.default_key_field

    def _get_fields_and_tables_parts_sql(self, current_table: ExchangeTableSettings,
                                         parent_table: ExchangeTableSettings | None = None,
                                         depth=0) -> dict[str, list | tuple]:
        """
        The method returns a data structure containing fields and tables.
        Based on this structure, an SQL query will be built.
        """
        result = {
            "fields": [],  # [(field, field_full_name, field_alias)]
            "tables": []  # [(table_with_alias, join_on)]
        }
        table_alias = self.get_table_alias(current_table)

        # Adding fields to result
        for field in current_table.fields:
            field_alias = self.get_field_alias(current_table, field)
            if parent_table is None:
                field_alias = current_table.aliases.get(field, field)
            field_full_name = self.get_full_field_name(table_alias, field)
            result["fields"].append((field, field_full_name, field_alias))

        # Adding current table to result
        result["tables"].append(self.get_table_with_joins(current_table, parent_table))

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
                                                parent_tables: list[ExchangeTableSettings] | None = None,
                                                depth=0, compare_field_actual_for_child_queries: bool | None = None):
        """
        A recursive query that forms a list of fields, tables and relationships between
        them for further formation of an SQL query
        """
        result = {}  # tracked_field: [(table_with_alias, join_on), ...]
        if parent_tables is None:
            parent_tables = [current_table]
        else:
            parent_tables.append(current_table)
        if current_table.field_actual_state_name:
            field_full_name = self.get_full_field_name(self.get_table_alias(current_table),
                                                        current_table.field_actual_state_name, False)

            first_table = parent_tables[0]
            key_field = self.get_table_key_field_name(first_table)
            key_field_full_name = self.get_full_field_name(self.get_table_alias(first_table), key_field)
            query_str_list = [
                "JOIN (\n  SELECT {0} AS \"id\", MAX({1}) AS \"{2}\"".format(key_field_full_name, field_full_name,
                                                                             self.TRACKED_FIELD_NAME),
            ]
            parent_table = None
            for table in parent_tables:
                table_str = "  FROM" if parent_table is None else "  JOIN"
                table_join = self.get_table_with_joins(table, parent_table)
                if table_join[1] is not None:
                    query_str_list.append("{0} {1} ON {2}".format(table_str, table_join[0], ", ".join(table_join[1])))
                else:
                    query_str_list.append("{0} {1}".format(table_str, table_join[0]))
                parent_table = table

            # A block that adds filtering of records in the child table if necessary.
            root_table = parent_tables[0]
            where_start = ""
            if (compare_field_actual_for_child_queries is True and
                    current_table.compare_field_actual_with_parent_query is not False and
                    root_table.field_actual_state_name):
                root_field = self.get_full_field_name(self.get_table_alias(root_table),
                                                       root_table.field_actual_state_name)
                where_start = "{} < {} AND".format(root_field, field_full_name)

            query_str_list.append("  WHERE {0} {1} {2}\n  GROUP BY {3}\n  ORDER BY {4}".
                                  format(where_start, field_full_name, self.WHERE_COMMENT,
                                         key_field_full_name, self.TRACKED_FIELD_NAME))
            if self.query_limit is not None:
                query_str_list.append("  LIMIT {} OFFSET %s".format(self.query_limit))
            query_str_list.append("  ) AS \"{0}\" ON {1} = \"{0}\".\"id\"".format(self.TRACKED_TABLE_NAME,
                                                                                  key_field_full_name))

            result[field_full_name] = "\n".join(query_str_list)

        if current_table.compare_field_actual_for_child_queries is not None:
            compare_field_actual_for_child_queries = current_table.compare_field_actual_for_child_queries
        if current_table.children is not None and depth < 2:
            for children_table in current_table.children:
                child_result = self._get_tracked_fields_with_related_tables(children_table, parent_tables, depth + 1,
                                                                            compare_field_actual_for_child_queries)
                result.update(child_result)

        parent_tables.pop()
        return result

    def get_tracked_fields_with_query(self):
        return self._get_tracked_fields_with_related_tables(self.source.table)

    def select_query_for_load(self, where_filter: str = "", adding_fields: [str] = [], adding_join: [str] = []) -> str:
        """
        Returns an SQL query based on the structure described in self.source.table.
        Request example:
            SELECT
                "fw"."id" AS "id",
                "fw"."title" AS "title",
                "fw"."description" AS "description",
                "fw"."rating" AS "imdb_rating",
                "fw"."modified" AS "modified",
                array_agg (DISTINCT "gr"."name") AS "genre",
                COALESCE (json_agg(DISTINCT jsonb_build_object(
                    'role', "pfw"."role",
                    'id', "pn"."id",
                    'name', "pn"."full_name",
                    'modified', "pn"."modified"
                )) FILTER (WHERE "pn"."modified" is not null), '[]') AS "persons",
                "_tracked_table"."_tracked_field"
            FROM "content"."film_work" AS "fw"
            LEFT JOIN "content"."genre_film_work" AS "gfw" ON ("fw"."id" = "gfw"."film_work_id")
            LEFT JOIN "content"."genre" AS "gr" ON ("gfw"."genre_id" = "gr"."id")
            LEFT JOIN "content"."person_film_work" AS "pfw" ON ("fw"."id" = "pfw"."film_work_id")
            LEFT JOIN "content"."person" AS "pn" ON ("pfw"."person_id" = "pn"."id")
            JOIN (
                SELECT "fw"."id" AS "id", MAX(pn.modified) AS "_tracked_field"
                FROM "content"."film_work" AS "fw"
                JOIN "content"."person_film_work" AS "pfw" ON "fw"."id" = "pfw"."film_work_id"
                JOIN "content"."person" AS "pn" ON "pfw"."person_id" = "pn"."id"
                WHERE "fw"."modified" < pn.modified AND pn.modified > %s
                GROUP BY "fw"."id"
                ORDER BY _tracked_field
                LIMIT 10000 OFFSET %s
            ) AS "_tracked_table" ON "fw"."id" = "_tracked_table"."id"
            GROUP BY
            "fw"."id",
            "fw"."title",
            "fw"."description",
            "fw"."rating",
            "fw"."modified",
            "_tracked_table"."_tracked_field"
            LIMIT 10000
        """
        fields_and_tables = self._get_fields_and_tables_parts_sql(self.source.table)
        tables = []
        for table in fields_and_tables["tables"]:
            tables.append(table[0] if table[1] is None else "LEFT JOIN {} ON ({})".format(table[0],
                                                                                          " AND ".join(table[1])))
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
