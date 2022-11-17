import abc
from typing import Any
from redis import Redis

from decorators import backoff

class BaseStorage:
    @abc.abstractmethod
    def save_state(self, state: dict) -> None:
        """Сохранить состояние в постоянное хранилище"""
        pass

    @abc.abstractmethod
    def retrieve_state(self) -> dict:
        """Загрузить состояние локально из постоянного хранилища"""
        pass


class RedisStorage(BaseStorage):
    STORAGE_NAME = "storage"

    def __init__(self, redis_adapter: Redis, storage_name: str = STORAGE_NAME):
        self.redis_adapter = redis_adapter
        self.storage_name = storage_name

    @backoff()
    def save_state(self, state: dict) -> None:
        self.redis_adapter.hset(self.storage_name, mapping=state)

    @backoff()
    def retrieve_state(self) -> dict:
        return self.redis_adapter.hgetall(self.storage_name)


class State:
    """
    Класс для хранения состояния при работе с данными, чтобы постоянно не перечитывать данные с начала.
    Здесь представлена реализация с сохранением состояния в файл.
    В целом ничего не мешает поменять это поведение на работу с БД или распределённым хранилищем.
    """

    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def set_state(self, key: str, value: Any) -> None:
        self.storage.save_state({key: value})

    def get_state(self, key: str, default: Any | None = None) -> Any:
        value = self.storage.retrieve_state().get(key.encode())
        if value is None:
            value = default
        elif type(value) == bytes:
            value = value.decode("utf-8")
        return value
