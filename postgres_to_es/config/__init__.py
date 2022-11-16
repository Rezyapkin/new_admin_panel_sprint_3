from pathlib import Path

from tomli import load as load_toml

from .models import Settings


with open(Path.joinpath(Path(__file__).parent, "settings.toml"), "rb") as fp:
    settings = Settings(etl_settings=load_toml(fp))
