import logging
import sys
import traceback
import inspect

from logs.configs import client_log_config, server_log_config

LOGGER = logging.getLogger('server') if sys.argv[0].find('client') == -1 else logging.getLogger('client')


def log(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        LOGGER.debug(f'Была вызвана функция {func.__name__} c параметрами {args}, {kwargs}.'
                     f'Вызов из модуля {func.__module__}.'
                     f'Вызов из функции {traceback.format_stack()[0].strip().split()[-1]}.'
                     f'Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)

        return res
    return wrapper

# вариант класса-декоратора
class Log:
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            res= func(*args, **kwargs)
            LOGGER.debug(f'Была вызвана функция {func.__name__} c параметрами {args}, {kwargs}. '
                         f'Вызов из модуля {func.__module__}. '
                         f'Вызов из функции {traceback.format_stack()[0].strip().split()[-1]}.'
                         f'Вызов из функции {inspect.stack()[1][3]}')
            return res
        return wrapper
