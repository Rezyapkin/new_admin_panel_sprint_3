"""Models loaded from configuration files and environment variables."""
from typing import Any, ForwardRef

from pydantic import BaseSettings, BaseModel, Field, PostgresDsn, validator


ExchangeTableSettings = ForwardRef("ExchangeTableSettings")


class ExchangeTableSettings(BaseModel):
    db_schema: str = Field("", alias="schema")
    name: str
    alias: str = ""
    key_field_name: str = ""
    fields: list[str] = []
    aliases: dict[str, str] = {}
    join: dict[str, str] = {}
    field_actual_state_name: str | None = None
    group: str | None = None
    children: list[ExchangeTableSettings] = []
    compare_field_actual_with_parent_query: bool | None = None
    compare_field_actual_for_child_queries: bool | None = None


ExchangeTableSettings.update_forward_refs()


class SQLDBSettings(BaseModel):
    db_schema: str = Field("default", alias="default_schema")
    key_field_name: str = "id"
    query_entries_limit: int | None


class EtlExchangeSettings(BaseModel):
    elastic_index: str
    transform_class: str
    mapping_file: str | None = None
    table: ExchangeTableSettings


class EtlSettings(BaseModel):
    etl_batch_size: int
    sql_db: SQLDBSettings
    bindings_elastic_to_sql: list[EtlExchangeSettings]


class Settings(BaseSettings):
    config_dir: str = ""
    db_timeout: int = 3
    pause_between_repeated_requests: int = 1
    etl_settings: EtlSettings
    es_host: str
    es_port: str
    postgres_server: str = Field(..., env="sql_host")
    postgres_user: str = Field(..., env="sql_user")
    postgres_password: str = Field(..., env="sql_password")
    postgres_db: str = Field(..., env="sql_database")
    postgres_dsn: PostgresDsn | None = None
    redis_host: str
    redis_port: str
    redis_etl_db: int = 0
    redis_password: str

    @validator("postgres_dsn", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("postgres_user"),
            password=values.get("postgres_password"),
            host=values.get("postgres_server"),
            path=f"/{values.get('postgres_db') or ''}",
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
