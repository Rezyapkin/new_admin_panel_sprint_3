from os import path

from psutil import process_iter, Process

from config import settings
from db_connection import postgres_db_connection
from pg_loader import PostgresSQLLoader
from datetime import datetime


# Check running same process.
def started_same_process() -> bool:
    current_process = Process()
    script_name = path.basename(__file__)
    find_same_process = False
    for process in process_iter(["pid", "name", "cmdline"]):
        '''
        Of course, it was possible to simply compare the cmdline of the process and current_process.
        But the script can be run with or without specifying the path to it.
        '''
        if process.name() == current_process.name() and process.pid != current_process.pid:
            for cmdline in current_process.cmdline():
                if cmdline.endswith(script_name):
                    find_same_process = True
                    break
    return find_same_process


def main() -> None:
    with postgres_db_connection(settings.postgres_dsn) as pg:
        pg_loader = PostgresSQLLoader(pg, settings.etl_settings.bindings_elastic_to_sql[0],
                                      settings.etl_settings.sql_db)
        for tracked_field in pg_loader.tracked_fields:
            for data, state_value, state_offset in pg_loader.load_data(tracked_field, "epoch"):
                print(state_value, state_offset)


if __name__ == "__main__":
    if started_same_process():
        print("The process has already been started")
    else:
        main()
