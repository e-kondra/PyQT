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
from PyQt5.QtWidgets import QApplication

from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, \
    MESSAGE_TEXT, MESSAGE, SENDER, DESTINATION, EXIT, RESPONSE_202, LIST_INFO, GET_CONTACTS, RESPONSE_200, \
    REMOVE_CONTACT, USERS_REQUEST, ADD_CONTACT
from common.utils import get_message, send_message
from descriptors import Port, Host
from logs.configs import server_log_config
from decors import log
from metaclasses import ServerVerifier
from server_database import ServerStorage
from tabulate import tabulate

from servergui import Ui_MainWindow, gui_create_model, HistoryWindow, gui_hist_model

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
    listen_address = Host()

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
        server_socket.settimeout(0.8)

        self.server_socket = server_socket

        self.server_socket.listen()

    def clients_message_handling(self, msg, client):
        global new_connection
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
                LOG.warning('Проверка сообщения в check_message не успешна, ответ: Имя пользователя уже занято ')
                send_message(client, {RESPONSE: 400, ERROR: 'Имя пользователя уже занято'})
                self.clients.remove(client)
                client.close()

        # 2. сообщение от одного клиента - другому
        elif ACTION in msg and msg[ACTION] == MESSAGE and TIME in msg and DESTINATION in msg \
                and SENDER in msg and MESSAGE_TEXT in msg:
            LOG.info('Получено сообщение в clients_message_handling, проверка успешна')
            self.database.process_message(msg[SENDER], msg[DESTINATION])
            self.message_list.append(msg)
            return

        # 3. выход
        elif ACTION in msg and msg[ACTION] == EXIT and ACCOUNT_NAME in msg:
            self.clients.remove(self.names[msg[ACCOUNT_NAME]])
            self.names[msg[ACCOUNT_NAME]].close()
            self.database.logout(msg[ACCOUNT_NAME]) # удаляем из таблицы активных пользователей
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
            print(f'msg[ACTION] = {msg[ACTION]}')
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
            send_message(client, {RESPONSE: 400, ERROR: 'Запрос не корректен'})
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

            try:
                if self.clients:
                    clients_read, clients_write, clients_exc = select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            if clients_read:
                for client in clients_read:
                    try:
                        clients_message = get_message(client)
                        LOG.info(f'Получено сообщение {clients_message} client={client}')
                        self.clients_message_handling(clients_message, client)

                    except Exception:
                        LOG.info(f'Клиент {client.getpeername()} отключился от сервера.')
                        self.clients.remove(client)
            # если сообщения для отправки есть , обрабатываем их
            if self.message_list:
                for i in self.message_list:
                    try:
                        self.message_handling(i, clients_write)
                    except Exception:
                        LOG.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                        self.clients.remove(self.names[i[DESTINATION]])
                        del self.names[i[DESTINATION]]
                self.message_list.clear()

def main():
    # Загрузка файла конфигурации сервера
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/{"server.ini"}')
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = arg_parser(config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    database = ServerStorage(os.path.join(config['SETTINGS']['Database_path'],config['SETTINGS']['Database_file']))

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Графический интерфейс для сервера
    APP = QApplication(sys.argv) # точка входа, создание приложения
    WINDOW_OBJ = Ui_MainWindow() # базовый класс для графич.элементов

    WINDOW_OBJ.statusBar().showMessage('Server Working') # внизу формы надпись
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
        print('show_history')
        global stat_window
        stat_window = HistoryWindow()
        print('show_history2')
        try:
            stat_window.history_table.setModel(gui_hist_model(database))
        except Exception as err:
            print(err)
        print('show_history3')
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()


    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    WINDOW_OBJ.refresh_button.triggered.connect(list_update)
    WINDOW_OBJ.show_history_button.triggered.connect(show_history)

    APP.exec_()



if __name__ == '__main__':
    main()