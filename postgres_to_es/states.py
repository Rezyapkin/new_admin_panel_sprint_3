import abc
from typing import Any
from redis import Redis


class BaseStorage:
    @abc.abstractmethod
    def save_state(self, state: dict) -> None:
        """Save state to persistent storage."""
        pass

    @abc.abstractmethod
    def retrieve_state(self) -> dict:
        """Load state locally from persistent storage."""
        pass


class RedisStorage(BaseStorage):
    STORAGE_NAME = "storage"

    def __init__(self, redis_adapter: Redis, storage_name: str = STORAGE_NAME):
        self.redis_adapter = redis_adapter
        self.storage_name = storage_name

    def save_state(self, state: dict) -> None:
        self.redis_adapter.hset(self.storage_name, mapping=state)

    def retrieve_state(self) -> dict:
        return self.redis_adapter.hgetall(self.storage_name)


class State:
    """
    A class for storing the state when working with data, so as not to constantly re-read the data from the beginning.
    Here is an implementation with saving the state to a file.
    In general, nothing prevents you from changing this behavior to work with a database or distributed storage.
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
