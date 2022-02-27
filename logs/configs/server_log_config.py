import logging
import logging.handlers as logging_handlers
import sys
import os

LOG = logging.getLogger('server')
LOG.setLevel(logging.DEBUG)

sys.path.append('../')

s_path = os.path.dirname(os.path.abspath(__file__))
dir = os.path.dirname(s_path)
s_path = os.path.join(dir, 'logs/server.log')

FILE_HANDLER = logging_handlers.TimedRotatingFileHandler(s_path, encoding='utf-8', when='midnight', interval=1)
FILE_HANDLER.setLevel(logging.DEBUG)

STREAM_HANDLER = logging.StreamHandler(sys.stdout)
STREAM_HANDLER.setLevel(logging.DEBUG)

FORMATTER_FILE = logging.Formatter("%(asctime)-20s %(filename)-10s %(levelname)-10s %(module)-20s %(message)s  ")
FORMATTER_STREAM = logging.Formatter("%(levelname)-10s %(filename)-10s %(asctime)-30s %(message)s  ")

FILE_HANDLER.setFormatter(FORMATTER_FILE)
STREAM_HANDLER.setFormatter(FORMATTER_STREAM)

LOG.addHandler(STREAM_HANDLER)
LOG.addHandler(FILE_HANDLER)



if __name__ == '__main__':
    LOG.critical('Внимание! навалило ошибок!')
    LOG.warning('Предупреждение!')
    LOG.debug('Выводим отладку')