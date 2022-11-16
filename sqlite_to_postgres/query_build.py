"""Module for generation SQL-query."""
from pydantic import BaseModel


def get_select_query_text(fields: [str], table_name: str, aliases: {} = {}) -> str:
    """Get SQL select query for table 'table_name' with fields.
    Args:
        fields: table fields involved in the sql query
        table_name: table name
        aliases: aliases for table fields

    Returns:
        Text SQL select query.
    """
    prepared_fields_list = []
    for field in fields:
        alias_as = " as \"{0}\"" if field in aliases else ""
        prepared_fields_list.append("\"{0}\"{1}".format(field, alias_as))
    str_fields = ", ".join(prepared_fields_list)
    return "SELECT {0} \nFROM {1}".format(str_fields, table_name)


def get_insert_query_for_model_text(model: BaseModel, table_name: str, conflict_fields: [] = []) -> str:
    """Get SQL insert query for table 'table_name'. Insert records - list Pydantic-model.
    Args:
        model: Pydantic model class for insert records.
        table_name: table name
        conflict_fields: list of fields that will be present in the CONFLICT ON zone.

    Returns:
        Text SQL insert query.
    """
    str_fields = ", ".join(["\"{0}\"".format(field) for field in model.__fields__.keys()])
    conflict_text = ""
    if len(conflict_fields) > 0:
        conflict_fields_str = ", ".join(["\"{}\"".format(field) for field in conflict_fields if field])
        conflict_text = "\nON CONFLICT ({0}) DO NOTHING".format(conflict_fields_str)
    return "INSERT INTO {0} ({1}) \nVALUES %s{2};".format(table_name, str_fields, conflict_text)


def get_template_insert_model(model: BaseModel):
    """Get a template for describing multiple insertion values.
        Args:
            model: Pydantic model class for insert records.
        Returns:
            Template for describing multiple insertion values.
        """
    str_fields = ", ".join(["%({0})s".format(field) for field in model.__fields__.keys()])
    return "({0})".format(str_fields)
