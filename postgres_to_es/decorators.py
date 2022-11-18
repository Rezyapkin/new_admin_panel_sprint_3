"""
A module with decorators that simplify error logging and reconnections.
"""
import logging

from functools import wraps
from time import sleep
from typing import Callable


def backoff(start_sleep_time: float = 0.1, factor: int = 2, border_sleep_time: float = 10,
            logger: Callable = logging.exception) -> Callable:
    """
    Функция для повторного выполнения функции через некоторое время, если возникла ошибка.
    Использует наивный экспоненциальный рост времени повтора (factor)
    до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * 2^(n) if t < border_sleep_time
        t = border_sleep_time if t >= border_sleep_time
    !!!Мне так больше по душе: Первый запуск и повторные после удачного запуска делаются сразу. А дальше по формуле
    :param start_sleep_time: начальное время повтора
    :param factor: во сколько раз нужно увеличить время ожидания
    :param border_sleep_time: граничное время ожидания
    :return: результат выполнения функции
    """
    def func_wrapper(func: Callable) -> Callable:

        @wraps(func)
        def inner(*args, **kwargs):
            pause = start_sleep_time
            while True:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger(e)

                sleep(pause)
                pause *= factor
                pause = border_sleep_time if pause > border_sleep_time else pause

        return inner

    return func_wrapper


def coroutine(coro):
    @wraps(coro)
    def coro_init(*args, **kwargs):
        fn = coro(*args, **kwargs)
        next(fn)
        return fn
    return coro_init
