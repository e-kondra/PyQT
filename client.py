import argparse
import sys
import threading
import time
from socket import *
import json
import logging
from threading import Thread

from PyQt5.QtWidgets import QApplication
from tabulate import tabulate

import logs.configs.client_log_config
from client.mainWindow import MainWindow
from client.transport import ClientTransport
from client.user_name_dialog import UserNameDialog
from client.database import ClientDatabase

from common.variables import *
from common.utils import send_message, get_message
from errors import ReqFieldMissingError, ServerError, IncorrectDataRecivedError
from decors import log
from metaclasses import ClientVerifier


database_lock = threading.Lock()
sock_lock = threading.Lock()

LOG = logging.getLogger('client')


@log
def arg_parser():
    '''Load common line options like
    # client.py 78.56.51.221 8888
    and read params and return 3 params: server_address, server_port, client_mode
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    # parser.add_argument('-m', '--mode', default=LISTEN_MODE, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    # client_mode = namespace.mode
    client_name = namespace.name

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        LOG.critical(
            f'Ошибка! Клиент с портом {server_port}. В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')
        sys.exit(1)

    return server_address, server_port, client_name


def main():
    # Сообщаем о запуске
    print('Консольный месседжер. Клиентский модуль.')
    # Загружаем параметы коммандной строки
    server_address, server_port, client_name = arg_parser()

    # клиентское приложение
    client_app = QApplication(sys.argv)

    if not client_name:
        dialog = UserNameDialog()
        client_app.exec_()
        if dialog.ok_pressed:
            client_name = dialog.user_name.text()
            del dialog
        else:
            exit(0)

    LOG.info(f'Запущен клиент со следующими параметрами: адрес {server_address}, порт {server_port}, имя пользователя {client_name}')


    database = ClientDatabase(client_name)

    try:
        transport = ClientTransport(database, client_name, server_port, server_address )
    except ServerError as err:
        print(err.text)
        exit(1)

    transport.setDaemon(True)
    transport.start()

    # GUI

    client_main_window = MainWindow(database, transport)
    client_main_window.make_connection(transport)
    client_main_window.setWindowTitle(f'Чат клиента {client_name}')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()

if __name__ == '__main__':
    main()
