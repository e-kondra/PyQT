import logging
import sys
import os

LOG = logging.getLogger('client')
LOG.setLevel(logging.DEBUG)

# sys.path.append('../')

cl_path = os.path.dirname(os.path.abspath(__file__))
dir = os.path.dirname(cl_path)
cl_path = os.path.join(dir, 'logs/client.log')

FILE_HANDLER = logging.FileHandler(cl_path, encoding='utf-8')
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
    LOG.error('Внимание! навалило ошибок!')
    LOG.warning('Предупреждение!')
