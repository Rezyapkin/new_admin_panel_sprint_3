import psycopg2
from psycopg2.extensions import connection as _connection
from psycopg2.extras import DictCursor
from pydantic import PostgresDsn
from redis import Redis

from decorators import backoff

@backoff()
def postgres_db_connection(pg_dsl: PostgresDsn, connect_timeout) -> _connection:
    return psycopg2.connect(pg_dsl, cursor_factory=DictCursor, connect_timeout=connect_timeout)

@backoff()
def redis_db_connection(host, port, num_db, password, connect_timeout) -> Redis:
    return Redis(host, port, num_db, password, connect_timeout)
