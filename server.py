# import configparser
# import json
# import os
# import sys
# import argparse
# import logging
# import threading
# from socket import socket, AF_INET, SOCK_STREAM
# import time
# import select
#
#
# from PyQt5.QtCore import QTimer
# from PyQt5.QtWidgets import QApplication, QMessageBox
#
# from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, \
#     MESSAGE_TEXT, MESSAGE, SENDER, DESTINATION, EXIT, RESPONSE_202, LIST_INFO, GET_CONTACTS, RESPONSE_200, \
#     REMOVE_CONTACT, USERS_REQUEST, ADD_CONTACT, RESPONSE_400
# from common.utils import *
# from descriptors import Port, Host
# from logs.configs import server_log_config
# from common.decors import log
# from metaclasses import ServerVerifier
# from server_database import ServerStorage
#
# from servergui import Ui_MainWindow, gui_create_model, HistoryWindow, gui_hist_model, ConfigWindow
#
# LOG = logging.getLogger('server')
#
# new_connection = False
# conflag_lock = threading.Lock()
#
#
# @log
# def arg_parser(default_port, default_address):
#     parser = argparse.ArgumentParser()
#     parser.add_argument('-p', default=default_port, type=int, nargs='?')
#     parser.add_argument('-a', default=default_address, nargs='?')
#     namespace = parser.parse_args(sys.argv[1:])
#     listen_address = namespace.a
#     listen_port = namespace.p
#     return listen_address, listen_port
#
#
# class Server(threading.Thread, metaclass=ServerVerifier):
#     listen_port = Port()
#
#     def __init__(self, listen_address, listen_port, database):
#         self.listen_address = listen_address
#         self.listen_port = listen_port
#
#         self.database = database
#
#         self.clients = []
#         self.message_list = []
#
#         # Словарь, содержащий имена пользователей и соответствующие им сокеты.
#         self.names = dict()
#         # Конструктор предка
#         super().__init__()
#
#     def socket_init(self):
#         # create servers socket
#         server_socket = socket(AF_INET, SOCK_STREAM)
#         server_socket.bind((self.listen_address, self.listen_port))
#         server_socket.settimeout(0.5)
#
#         self.server_socket = server_socket
#
#         self.server_socket.listen()
#
#     def clients_message_handling(self, msg, client):
#         global new_connection
#         LOG.debug(f'Разбор сообщения от клиента: {msg}')
#         # 1.Сообщение о присутствии
#         if ACTION in msg and msg[ACTION] == PRESENCE and TIME in msg and USER in msg:
#             if msg[USER][ACCOUNT_NAME] not in self.names.keys():
#                 self.names[msg[USER][ACCOUNT_NAME]] = client
#                 client_ip, client_port = client.getpeername()
#                 # в БД регистрируем подключение пользователя или создаем его при необходимости
#                 self.database.login(msg[USER][ACCOUNT_NAME], client_ip, client_port)
#                 LOG.info('Проверка сообщения в clients_message_handling успешна, ответ: 200')
#                 send_message(client, {RESPONSE: 200})
#                 with conflag_lock:  # add_new
#                     new_connection = True
#             else:
#                 response = RESPONSE_400
#                 response[ERROR] = 'Имя пользователя уже занято'
#                 LOG.warning('Проверка сообщения в check_message не успешна, ответ: Имя пользователя уже занято ')
#                 send_message(client, response)
#                 self.clients.remove(client)
#                 client.close()
#
#         # 2. сообщение от одного клиента - другому
#         elif ACTION in msg and msg[ACTION] == MESSAGE and TIME in msg and DESTINATION in msg \
#                 and SENDER in msg and MESSAGE_TEXT in msg and self.names[msg[SENDER]] == client:
#             if msg[DESTINATION] in self.names:
#                 self.message_list.append(msg)
#                 self.database.process_message(msg[SENDER], msg[DESTINATION])
#                 send_message(client, RESPONSE_200)
#             else:
#                 response = RESPONSE_400
#                 response[ERROR] = 'Пользователь не зарегистрирован на сервере'
#                 send_message(client, response)
#             return
#
#         # 3. выход
#         elif ACTION in msg and msg[ACTION] == EXIT and ACCOUNT_NAME in msg \
#                 and self.names[msg[ACCOUNT_NAME]] == client:
#             self.clients.remove(self.names[msg[ACCOUNT_NAME]])
#             self.names[msg[ACCOUNT_NAME]].close()
#             self.database.logout(msg[ACCOUNT_NAME])  # удаляем из таблицы активных пользователей
#             del self.names[msg[ACCOUNT_NAME]]
#             with conflag_lock:
#                 new_connection = True
#             return
#
#         # 4. добавление контакта
#         elif ACTION in msg and msg[ACTION] == ADD_CONTACT and ACCOUNT_NAME in msg and USER in msg \
#                 and self.names[msg[USER]] == client:
#             self.database.add_contact(msg[USER], msg[ACCOUNT_NAME])
#             send_message(client, RESPONSE_200)
#
#         # 5. удаление контакта
#         elif ACTION in msg and msg[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in msg and USER in msg \
#                 and self.names[msg[USER]] == client:
#             self.database.remove_contact(msg[USER], msg[ACCOUNT_NAME])
#             send_message(client, RESPONSE_200)
#
#         # 6. запрос известных пользователей
#         elif ACTION in msg and msg[ACTION] == USERS_REQUEST and ACCOUNT_NAME in msg \
#                 and self.names[msg[ACCOUNT_NAME]] == client:
#             response = RESPONSE_202
#             response[LIST_INFO] = [user[0] for user in self.database.users_list()]
#             send_message(client, response)
#
#         # 7. запрос контакт-листа
#         elif ACTION in msg and msg[ACTION] == GET_CONTACTS and USER in msg and self.names[msg[USER]] == client:
#             response = RESPONSE_202
#             try:
#                 response[LIST_INFO] = self.database.get_contacts(msg[USER])
#             except Exception as err:
#                 print(err)
#             print(f'response[LIST_INFO] = {response[LIST_INFO]}')
#             send_message(client, response)
#             print(f'response = {response}')
#         else:
#             LOG.warning('Проверка сообщения в check_message не успешна, ответ: Запрос не корректен ')
#             response = RESPONSE_400
#             response[ERROR] = 'Запрос не корректен'
#             send_message(client, response)
#             return
#
#     def message_handling(self, msg, clients_wr):
#         # msg[DESTINATION] - имя
#         # names[message[DESTINATION]] - получатель
#
#         if msg[DESTINATION] in self.names and self.names[msg[DESTINATION]] in clients_wr:
#             send_message(self.names[msg[DESTINATION]], msg)
#             LOG.info(f'Пользователю {msg[DESTINATION]} отправлено сообщение от {msg[SENDER]}')
#         elif msg[DESTINATION] in self.names and self.names[msg[DESTINATION]] not in clients_wr:
#             raise ConnectionError
#         else:
#             LOG.error(f'Пользователь {msg[DESTINATION]} не зарегистрирован, отправка сообщения невозможна')
#
#     def run(self):
#
#         global new_connection
#         self.socket_init()
#         # endless cycle to waiting clients
#         while True:
#             # connecting
#             try:
#                 client_socket, client_addr = self.server_socket.accept()
#             except OSError:
#                 pass
#             else:
#                 LOG.info(f'Соединение установлено c {client_addr}')
#                 self.clients.append(client_socket)
#
#             clients_read = []
#             clients_write = []
#             clients_exc = []
#
#             # проверка наличия ждущих клиентов
#             try:
#                 if self.clients:
#                     clients_read, clients_write, clients_exc = select.select(self.clients, self.clients, [], 0)
#             except OSError:
#                 pass
#             # прием сообщения и если ошибка, исключаем клиента
#             if clients_read:
#                 for client in clients_read:
#                     try:
#                         clients_message = get_message(client)
#                         LOG.info(f'Получено сообщение {clients_message} client={client}')
#                         self.clients_message_handling(clients_message, client)
#
#                     except (OSError):
#                         # Ищем клиента в словаре клиентов и удаляем его из него и  базы подключённых
#                         LOG.info(f'Клиент {client.getpeername()} отключился от сервера.')
#                         for name in self.names:
#                             if self.names[name] == client:
#                                 self.database.user_logout(name)
#                                 del self.names[name]
#                                 break
#                         self.clients.remove(client)
#                         with conflag_lock:
#                             new_connection = True
#             # если сообщения для отправки есть , обрабатываем их
#             for i in self.message_list:
#                 try:
#                     self.message_handling(i, clients_write)
#                 except Exception:
#                     LOG.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
#                     self.clients.remove(self.names[i[DESTINATION]])
#                     self.database.user_logout(i[DESTINATION])
#                     del self.names[i[DESTINATION]]
#                     with conflag_lock:
#                         new_connection = True
#             self.message_list.clear()
#
#
# def config_load():
#     config = configparser.ConfigParser()
#     dir_path = os.path.dirname(os.path.realpath(__file__))
#     config.read(f'{dir_path}/{"server.ini"}')
#
#     if 'SETTINGS' in config:
#         return config
#     else:
#         config.add_section('SETTINGS')
#         config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
#         config.set('SETTINGS', 'Listen_Address', '')
#         config.set('SETTINGS', 'Database_path', '')
#         config.set('SETTINGS', 'Database_file', 'server_database.db3')
#         return config
#
#
# def main():
#     # Загрузка файла конфигурации сервера
#     config = config_load()
#     dir_path = os.path.dirname(os.path.realpath(__file__))
#     config.read(f"{dir_path}/{'server.ini'}")
#     # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
#     listen_address, listen_port = arg_parser(config['SETTINGS']['Default_port'],
#                                              config['SETTINGS']['Listen_Address'])
#
#     database = ServerStorage(os.path.join(config['SETTINGS']['Database_path'],
#                                           config['SETTINGS']['Database_file']))
#
#     # Создание экземпляра класса - сервера.
#     server = Server(listen_address, listen_port, database)
#     server.daemon = True
#     server.start()
#
#     # Графический интерфейс для сервера
#     server_app = QApplication(sys.argv)  # точка входа, создание приложения
#     window_obj = Ui_MainWindow()  # базовый класс для графич.элементов
#
#     window_obj.statusBar().showMessage('Server Working')  # внизу формы надпись
#     window_obj.active_clients_table.setModel(
#         gui_create_model(database))  # заполняем таблицу основного окна делаем разметку и заполянем ее
#     window_obj.active_clients_table.resizeColumnsToContents()
#     window_obj.active_clients_table.resizeRowsToContents()
#
#     # Функция обновляет данные по активным клиентам
#     def list_update():
#         global new_connection
#         # LOG.info(new_connection)
#         if new_connection:
#             LOG.info(new_connection)
#             window_obj.active_clients_table.setModel(
#                 gui_create_model(database))
#             window_obj.active_clients_table.resizeColumnsToContents()
#             window_obj.active_clients_table.resizeRowsToContents()
#             with conflag_lock:
#                 new_connection = False
#
#     # Функция создающяя окно с историей клиентов
#     def show_history():
#         global stat_window
#         stat_window = HistoryWindow()
#         try:
#             stat_window.history_table.setModel(gui_hist_model(database))
#         except Exception as err:
#             print(err)
#         stat_window.history_table.resizeColumnsToContents()
#         stat_window.history_table.resizeRowsToContents()
#         stat_window.show()
#
#     def server_config():
#         global config_window
#         # Создаём окно и заносим в него текущие параметры
#         config_window = ConfigWindow()
#         config_window.db_path.insert(config['SETTINGS']['Database_path'])
#         config_window.db_file.insert(config['SETTINGS']['Database_file'])
#         config_window.port.insert(config['SETTINGS']['Default_port'])
#         config_window.ip.insert(config['SETTINGS']['Listen_Address'])
#         config_window.save_btn.clicked.connect(save_server_config)
#
#     # сохранение настроек
#     def save_server_config():
#         global config_window
#         message = QMessageBox()
#         config['SETTINGS']['Database_path'] = config_window.db_path.text()
#         config['SETTINGS']['Database_file'] = config_window.db_file.text()
#         try:
#             port = int(config_window.port.text())
#         except ValueError:
#             message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
#         else:
#             config['SETTINGS']['Listen_Address'] = config_window.ip.text()
#             if 1023 < port < 65536:
#                 config['SETTINGS']['Default_port'] = str(port)
#                 print(port)
#                 with open('server.ini', 'w') as conf:
#                     config.write(conf)
#                     message.information(
#                         config_window, 'OK', 'Настройки успешно сохранены!')
#             else:
#                 message.warning(
#                     config_window,
#                     'Ошибка',
#                     'Порт должен быть от 1024 до 65536')
#
#     # Таймер, обновляющий список клиентов 1 раз в секунду
#     timer = QTimer()
#     timer.timeout.connect(list_update)
#     timer.start(1000)
#
#     # Связываем кнопки с процедурами
#     window_obj.refresh_button.triggered.connect(list_update)
#     window_obj.show_history_button.triggered.connect(show_history)
#     window_obj.config_btn.triggered.connect(server_config)
#
#     server_app.exec_()
#
#
# if __name__ == '__main__':
#     main()


import socket
import sys
import os
import argparse
import json
import logging
import select
import time
import threading
import configparser
# import logs.config_server_log
from logs.configs import server_log_config
from common.variables import *
from common.utils import *
from common.decors import log
from descriptors import Port
from metaclasses import ServerVerifier
from server_database import ServerStorage
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from servergui import Ui_MainWindow, gui_create_model, HistoryWindow, gui_hist_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem

# Инициализация логирования сервера.
LOG = logging.getLogger('server')

# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()


# Парсер аргументов коммандной строки.
@log
def arg_parser(default_port, default_address):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


# Основной класс сервера
class Server(threading.Thread, metaclass=ServerVerifier):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        # Параментры подключения
        self.addr = listen_address
        self.port = listen_port

        # База данных сервера
        self.database = database

        # Список подключённых клиентов.
        self.clients = []
        # Список сообщений на отправку.
        self.messages = []

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

        # Конструктор предка
        super().__init__()

    def init_socket(self):
        LOG.info(
            f'Запущен сервер, порт для подключений: {self.port} , адрес с которого принимаются подключения: {self.addr}. Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        # Начинаем слушать сокет.
        self.sock = transport
        self.sock.listen()

    def run(self):
        # Инициализация Сокета
        global new_connection
        self.init_socket()

        # Основной цикл программы сервера
        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                LOG.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError as err:
                LOG.error(f'Ошибка работы с сокетами: {err}')

            # принимаем сообщения и если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except (OSError):
                        # Ищем клиента в словаре клиентов и удаляем его из него и  базы подключённых
                        LOG.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        for name in self.names:
                            if self.names[name] == client_with_message:
                                self.database.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client_with_message)
                        with conflag_lock:
                            new_connection = True

            # Если есть сообщения, обрабатываем каждое.
            for message in self.messages:
                try:
                    self.process_message(message, send_data_lst)
                except (ConnectionAbortedError, ConnectionError, ConnectionResetError, ConnectionRefusedError):
                    LOG.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    self.database.user_logout(message[DESTINATION])
                    del self.names[message[DESTINATION]]
                    with conflag_lock:
                        new_connection = True
            self.messages.clear()

    # Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение, список зарегистрированых
    # пользователей и слушающие сокеты. Ничего не возвращает.
    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            LOG.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            LOG.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    # Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента, проверяет корректность, отправляет
    #     словарь-ответ в случае необходимости.
    def process_client_message(self, message, client):
        global new_connection
        LOG.debug(f'Разбор сообщения от клиента : {message}')

        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return

        # Если это сообщение, то добавляем его в очередь сообщений. проверяем наличие в сети. и отвечаем.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and self.names[message[SENDER]] == client:
            if message[DESTINATION] in self.names:
                self.messages.append(message)
                self.database.process_message(message[SENDER], message[DESTINATION])
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                send_message(client, response)
            return

        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            LOG.info(f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return

        # Если это запрос контакт-листа
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and \
                self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)

        # Если это добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]
            send_message(client, response)

        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


# Загрузка файла конфигурации
def config_load():
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по умолчанию.
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

    # Инициализация базы данных
    database = ServerStorage(os.path.join(config['SETTINGS']['Database_path'], config['SETTINGS']['Database_file']))

    # Создание экземпляра класса - сервера и его запуск:
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Создаём графическое окуружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = Ui_MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция обновляющяя список подключённых, проверяет флаг подключения, и если надо обновляет список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Функция создающяя окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(gui_hist_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
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
                dir_path = os.path.dirname(os.path.realpath(__file__))
                with open(f"{dir_path}/{'server.ini'}", 'w') as conf:
                    config.write(conf)
                    message.information(config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(config_window, 'Ошибка', 'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()
