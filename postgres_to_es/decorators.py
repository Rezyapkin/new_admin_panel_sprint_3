import logging

from functools import wraps
from time import sleep
from typing import Callable


def backoff(start_sleep_time: float = 0.1, factor: int = 2, border_sleep_time: float = 10) -> Callable:
    '''
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
    '''
    def func_wrapper(func: Callable) -> Callable:
        pause = 0

        @wraps(func)
        def inner(*args, **kwargs):
            nonlocal pause
            if pause > 0:
                sleep(pause)
                pause *= factor
                pause = border_sleep_time if pause > border_sleep_time else pause
            else:
                pause = start_sleep_time
            result = func(*args, **kwargs)
            pause = 0
            return result

        return inner

    return func_wrapper


def coroutine(coro):
    @wraps(coro)
    def coro_init(*args, **kwargs):
        fn = coro(*args, **kwargs)
        next(fn)
        return fn
    return coro_init


def repeat_request(exception):
    def func_wrapper(func: Callable):
        @wraps(func)
        def inner(*args, **kwargs):
            try:
                while True:
                    return func(*args, **kwargs)
            except exception as e:
                logging.log(logging.WARNING, e)

        return inner

    return func_wrapper