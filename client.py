'''
Основной модуль клиентского приложения
'''
import logging
import argparse
import sys
import os

from Cryptodome.PublicKey import RSA
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.errors import ServerError
from common.decors import log
from common.variables import DEFAULT_IP_ADDRESS, DEFAULT_PORT
from client.database import ClientDatabase
from client.transport import ClientTransport
from client.main_window import ClientMainWindow
from client.user_name_dialog import UserNameDialog
import logs.configs.client_log_config


LOG = logging.getLogger('client')


# Парсер аргументов коммандной строки
@log
def arg_parser():
    '''
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов
    адрес сервера, порт, имя пользователя, пароль.
    Выполняет проверку на корректность номера порта.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        LOG.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}.'
            f' Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return server_address, server_port, client_name, client_passwd



if __name__ == '__main__':
    """Основная функция клиента"""
    # Загружаем параметы коммандной строки
    server_address, server_port, client_name, client_passwd = arg_parser()
    LOG.debug('Args loaded')

    # Создаём клиентокое приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его
    start_dialog = UserNameDialog()
    if not client_name or not client_passwd:
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и
        # удаляем объект, инааче выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()
            LOG.debug(f'Using USERNAME = {client_name}, PASSWD = {client_passwd}.')
        else:
            exit(0)

    # Записываем логи
    LOG.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address},'
        f' порт: {server_port}, имя пользователя: {client_name}')

    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    #!!!keys.publickey().export_key()
    LOG.debug("Keys sucsessfully loaded.")
    # Создаём объект базы данных
    database = ClientDatabase(client_name)
    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(
            {'port': server_port, 'ip_address': server_address, 'database': database,
             'username': client_name, 'passwd': client_passwd, 'keys': keys})
        LOG.debug("Transport ready.")
    except ServerError as error:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Удалим объект диалога , он больше не нужен
    del start_dialog

    # GUI
    main_window = ClientMainWindow(database, transport, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат клиента - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, то закрываем транспорт
    transport.transport_shutdown()
    transport.join()
