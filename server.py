import configparser
import json
import os
import sys
import logging
import threading
from datetime import time
from socket import socket, AF_INET, SOCK_STREAM
import time
from select import select
import argparse

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, \
    MESSAGE_TEXT, MESSAGE, SENDER, DESTINATION, EXIT, RESPONSE_202, LIST_INFO, GET_CONTACTS, RESPONSE_200, \
    REMOVE_CONTACT, USERS_REQUEST, ADD_CONTACT, RESPONSE_400
from common.utils import get_message, send_message
from descriptors import Port, Host
from logs.configs import server_log_config
from common.decors import log
from metaclasses import ServerVerifier
from server_database import ServerStorage
from tabulate import tabulate

from servergui import Ui_MainWindow, gui_create_model, HistoryWindow, gui_hist_model, ConfigWindow

LOG = logging.getLogger('server')

new_connection = False
conflag_lock = threading.Lock()


@log
def arg_parser(default_port, default_address):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(threading.Thread, metaclass=ServerVerifier):
    listen_port = Port()

    def __init__(self, listen_address, listen_port, database):
        self.listen_address = listen_address
        self.listen_port = listen_port

        self.database = database

        self.clients = []
        self.message_list = []

        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        self.names = dict()
        # Конструктор предка
        super().__init__()

    def socket_init(self):
        # create servers socket
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind((self.listen_address, self.listen_port))
        server_socket.settimeout(0.5)

        self.server_socket = server_socket

        self.server_socket.listen()

    def clients_message_handling(self, msg, client):
        global new_connection
        LOG.debug(f'Разбор сообщения от клиента: {msg}')
        # 1.Сообщение о присутствии
        if ACTION in msg and msg[ACTION] == PRESENCE and TIME in msg and USER in msg:
            if msg[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[msg[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                # в БД регистрируем подключение пользователя или создаем его при необходимости
                self.database.login(msg[USER][ACCOUNT_NAME], client_ip, client_port)
                LOG.info('Проверка сообщения в clients_message_handling успешна, ответ: 200')
                send_message(client, {RESPONSE: 200})
                with conflag_lock:  # add_new
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято'
                LOG.warning('Проверка сообщения в check_message не успешна, ответ: Имя пользователя уже занято ')
                send_message(client, response)
                self.clients.remove(client)
                client.close()

        # 2. сообщение от одного клиента - другому
        elif ACTION in msg and msg[ACTION] == MESSAGE and TIME in msg and DESTINATION in msg \
                and SENDER in msg and MESSAGE_TEXT in msg and self.names[msg[SENDER]] == client:
            if msg[DESTINATION] in self.names:
                self.message_list.append(msg)
                self.database.process_message(msg[SENDER], msg[DESTINATION])
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере'
                send_message(client, response)
            return

        # 3. выход
        elif ACTION in msg and msg[ACTION] == EXIT and ACCOUNT_NAME in msg \
                and self.names[msg[ACCOUNT_NAME]] == client:
            self.clients.remove(self.names[msg[ACCOUNT_NAME]])
            self.names[msg[ACCOUNT_NAME]].close()
            self.database.logout(msg[ACCOUNT_NAME])  # удаляем из таблицы активных пользователей
            del self.names[msg[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return

        # 4. добавление контакта
        elif ACTION in msg and msg[ACTION] == ADD_CONTACT and ACCOUNT_NAME in msg and USER in msg \
                and self.names[msg[USER]] == client:
            self.database.add_contact(msg[USER], msg[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # 5. удаление контакта
        elif ACTION in msg and msg[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in msg and USER in msg \
                and self.names[msg[USER]] == client:
            self.database.remove_contact(msg[USER], msg[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # 6. запрос известных пользователей
        elif ACTION in msg and msg[ACTION] == USERS_REQUEST and ACCOUNT_NAME in msg \
                and self.names[msg[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]
            send_message(client, response)

        # 7. запрос контакт-листа
        elif ACTION in msg and msg[ACTION] == GET_CONTACTS and USER in msg and self.names[msg[USER]] == client:
            response = RESPONSE_202
            try:
                response[LIST_INFO] = self.database.get_contacts(msg[USER])
            except Exception as err:
                print(err)
            print(f'response[LIST_INFO] = {response[LIST_INFO]}')
            send_message(client, response)
            print(f'response = {response}')
        else:
            LOG.warning('Проверка сообщения в check_message не успешна, ответ: Запрос не корректен ')
            response = RESPONSE_400
            response[ERROR] = 'Запрос не корректен'
            send_message(client, response)
            return

    def message_handling(self, msg, clients_wr):
        # msg[DESTINATION] - имя
        # names[message[DESTINATION]] - получатель

        if msg[DESTINATION] in self.names and self.names[msg[DESTINATION]] in clients_wr:
            send_message(self.names[msg[DESTINATION]], msg)
            LOG.info(f'Пользователю {msg[DESTINATION]} отправлено сообщение от {msg[SENDER]}')
        elif msg[DESTINATION] in self.names and self.names[msg[DESTINATION]] not in clients_wr:
            raise ConnectionError
        else:
            LOG.error(f'Пользователь {msg[DESTINATION]} не зарегистрирован, отправка сообщения невозможна')

    def run(self):

        global new_connection
        self.socket_init()
        # endless cycle to waiting clients
        while True:
            # connecting
            try:
                client_socket, client_addr = self.server_socket.accept()
            except OSError:
                pass
            else:
                LOG.info(f'Соединение установлено c {client_addr}')
                self.clients.append(client_socket)

            clients_read = []
            clients_write = []
            clients_exc = []

            # проверка наличия ждущих клиентов
            try:
                if self.clients:
                    clients_read, clients_write, clients_exc = select(self.clients, self.clients, [], 0)
            except OSError:
                pass
            # прием сообщения и если ошибка, исключаем клиента
            if clients_read:
                for client in clients_read:
                    try:
                        clients_message = get_message(client)
                        LOG.info(f'Получено сообщение {clients_message} client={client}')
                        self.clients_message_handling(clients_message, client)

                    except (OSError):
                        # Ищем клиента в словаре клиентов и удаляем его из него и  базы подключённых
                        LOG.info(f'Клиент {client.getpeername()} отключился от сервера.')
                        for name in self.names:
                            if self.names[name] == client:
                                self.database.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client)
                        with conflag_lock:
                            new_connection = True
            # если сообщения для отправки есть , обрабатываем их
            for i in self.message_list:
                try:
                    self.message_handling(i, clients_write)
                except Exception:
                    LOG.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[i[DESTINATION]])
                    self.database.user_logout(i[DESTINATION])
                    del self.names[i[DESTINATION]]
                    with conflag_lock:
                        new_connection = True
            self.message_list.clear()

def config_load():
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/{"server.ini"}')

    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config

def main():
    # Загрузка файла конфигурации сервера
    config = config_load()

    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = arg_parser(config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    database = ServerStorage(os.path.join(config['SETTINGS']['Database_path'], config['SETTINGS']['Database_file']))

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Графический интерфейс для сервера
    APP = QApplication(sys.argv)  # точка входа, создание приложения
    WINDOW_OBJ = Ui_MainWindow()  # базовый класс для графич.элементов

    WINDOW_OBJ.statusBar().showMessage('Server Working')  # внизу формы надпись
    WINDOW_OBJ.active_clients_table.setModel(
        gui_create_model(database))  # заполняем таблицу основного окна делаем разметку и заполянем ее
    WINDOW_OBJ.active_clients_table.resizeColumnsToContents()
    WINDOW_OBJ.active_clients_table.resizeRowsToContents()

    # Функция обновляет данные по активным клиентам
    def list_update():
        global new_connection
        # LOG.info(new_connection)
        if new_connection:
            LOG.info(new_connection)
            WINDOW_OBJ.active_clients_table.setModel(
                gui_create_model(database))
            WINDOW_OBJ.active_clients_table.resizeColumnsToContents()
            WINDOW_OBJ.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Функция создающяя окно с историей клиентов
    def show_history():
        global stat_window
        stat_window = HistoryWindow()
        try:
            stat_window.history_table.setModel(gui_hist_model(database))
        except Exception as err:
            print(err)
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # сохранение настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    WINDOW_OBJ.refresh_button.triggered.connect(list_update)
    WINDOW_OBJ.show_history_button.triggered.connect(show_history)
    WINDOW_OBJ.config_btn.triggered.connect(server_config)

    APP.exec_()


if __name__ == '__main__':
    main()

