"""Connect dynconf for application-settings."""
from os import path
from dynaconf import Dynaconf


config_dir = path.dirname(path.abspath(__file__))

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=[path.join(config_dir, "settings.toml"), path.join(config_dir, ".secrets.toml")],
)

settings.app_dir = config_dir
settings.pg_dsl = {
    "dbname": settings.pg_db_name,
    "user": settings.pg_db_user,
    "password": settings.pg_db_password,
    "host": settings.get("pg_db_host", default="127.0.0.1"),
    "port": settings.get("pg_db_port", default=5432),
}

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
