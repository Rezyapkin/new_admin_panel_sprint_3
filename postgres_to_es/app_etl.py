import logging
from contextlib import closing
from pathlib import Path
from psutil import process_iter, Process

from config import settings
from db_connection import redis_db_connection, elastic_search_connection
from es_load import MoviesESLoad
from etl_process import ProcessETL
from states import State, RedisStorage


def main() -> None:
    with (closing(redis_db_connection(settings.redis_host, settings.redis_port, settings.redis_etl_db,
                                      settings.redis_password, connect_timeout=settings.db_timeout)) as redis_adapter,
          closing(elastic_search_connection(settings.es_host, settings.es_port, settings.db_timeout))
          as elastic_adapter):
        ProcessETL(settings, State(RedisStorage(redis_adapter)), MoviesESLoad(elastic_adapter)).start()


# Check running same process.
def started_same_process() -> bool:
    """Checks if a python script with the same name is running."""
    current_process = Process()
    script_name = Path(__file__).name
    find_same_process = False
    for process in process_iter(["pid", "name", "cmdline"]):
        if process.name() == current_process.name() and process.pid != current_process.pid:
            for cmdline in current_process.cmdline():
                if cmdline.endswith(script_name):
                    find_same_process = True
                    break
    return find_same_process


if __name__ == "__main__":
    if started_same_process():
        logging.log(logging.WARNING, "The process has already been started")
    else:
        main()
