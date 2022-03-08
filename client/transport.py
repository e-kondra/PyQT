# import json
# import threading
# import time
# import sys
# sys.path.append('../')
# from socket import socket, AF_INET, SOCK_STREAM
#
# from PyQt5.QtCore import QObject, pyqtSignal
#
#
# from common.utils import send_message, get_message
# from common.variables import *
# from common.errors import ServerError
# from logs.configs.client_log_config import LOG
#
# socket_lock = threading.Lock()
# # класс, отвечающий за взаимодействие с сервером
# class ClientTransport(threading.Thread, QObject):
#
#     new_message = pyqtSignal(str) # сигнал новое сообщение
#     connection_lost = pyqtSignal() # сигнал потери соединения
#
#     def __init__(self, database, username, port, ip_address):
#         # конструкторы предков вызываем
#         threading.Thread.__init__(self)
#         QObject.__init__(self)
#
#         self.database = database
#         self.username = username
#         self.transport = None
#
#         self.connection_init(port, ip_address)
#
#         try:
#             self.user_list_request()
#             self.contacts_list_request()
#         except OSError as err:
#             if err.errno:
#                 LOG.critical(f'Потеряно соединение с сервером.')
#                 raise ServerError('Потеряно соединение с сервером!')
#             LOG.error('Timeout соединения при обновлении списков пользователей.')
#         except json.JSONDecodeError:
#             LOG.critical(f'Потеряно соединение с сервером.')
#             raise ServerError('Потеряно соединение с сервером!')
#             # Флаг продолжения работы транспорта.
#         self.running = True
#
#     # cоединение с сокетом.
#     def connection_init(self, port, ip_address):
#
#         self.transport = socket(AF_INET, SOCK_STREAM)
#         self.transport.settimeout(5)
#
#         # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
#         connected= False
#         for i in range(5):
#             LOG.info(f'{i} попытка подключения к серверу')
#             try:
#                 self.transport.connect((ip_address, port))
#             except (ConnectionRefusedError, OSError):
#                 pass
#             else:
#                 connected = True
#                 LOG.debug('Установлено соединение с сервером')
#                 break
#             time.sleep(1)
#
#         if not connected:
#             LOG.critical(
#                 f'Не удалось подключиться к серверу {ip_address}:{port}, '
#                 f'конечный компьютер отверг запрос на подключение.')
#             raise ServerError('Не удалось установить соединение с сервером')
#
#         # Посылаем серверу приветственное сообщение и получаем ответ что всё нормально или ловим исключение
#         try:
#             with socket_lock:
#                 try:
#                     send_message(self.transport, self.make_presence())
#                     LOG.debug('send_message')
#                 except Exception as err:
#                     LOG.warning(f'send_message error : {err}')
#                 try:
#                     self.get_server_answer(get_message(self.transport))
#                     LOG.debug('get_server_answer')
#                 except Exception as err:
#                     LOG.warning(f'get_server_answer error : {err}')
#
#         except (OSError, json.JSONDecodeError):
#             LOG.critical('Потеряно соединение с сервером!!!')
#             raise ServerError('Потеряно соединение с сервером')
#
#         LOG.info('Соединение с сервером установлено')
#
#     def make_presence(self):
#         '''generate clients presence request'''
#         request = {
#             ACTION: PRESENCE,
#             TIME: time.time(),
#             USER: {
#                 ACCOUNT_NAME: self.username
#             }
#         }
#         return request
#
#     def get_server_answer(self, msg):
#         '''get answer from server'''
#         LOG.debug(f'Разбор сообщения от сервера{msg}')
#
#         print(msg)
#         print(f'msg[RESPONSE] = {msg[RESPONSE]}')
#         if RESPONSE in msg:
#             if msg[RESPONSE] == 200:
#                 return
#             elif msg[RESPONSE] == 400:
#                 raise ServerError(f'{msg[ERROR]}')
#             else:
#                 LOG.debug(f'Не известный код подтверждения! {msg[RESPONSE]}')
#         # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
#         elif ACTION in msg and msg[ACTION] == MESSAGE and SENDER in msg and DESTINATION in msg \
#                             and MESSAGE_TEXT in msg and msg[DESTINATION] == self.username:
#             print(f'\nПолучено сообщение от пользователя {msg[SENDER]}: \n{msg[MESSAGE_TEXT]}')
#             LOG.de(f'\nПолучено сообщение от пользователя {msg[SENDER]}: \n{msg[MESSAGE_TEXT]}')
#             self.database.save_message(msg[SENDER], 'in', msg[MESSAGE_TEXT])
#             self.new_message.emit(msg[SENDER]) # свой сигнал!
#
#     # запрос/овновление списка известных пользователей
#     def user_list_request(self):
#         LOG.debug(f'Запрос списка известных пользователей {self.username}')
#         req = {
#             ACTION: USERS_REQUEST,
#             TIME: time.time(),
#             ACCOUNT_NAME: self.username
#         }
#         with socket_lock:
#             send_message(self.transport, req)
#             ans = get_message(self.transport)
#         if RESPONSE in ans and ans[RESPONSE] == 202:
#             self.database.add_users(ans[LIST_INFO])
#         else:
#             LOG.error('Не удалось обновить список известных пользователей')
#
#     # запрос/обновление списка контактов пользователя
#     def contacts_list_request(self):
#         LOG.debug(f'Запрос контакт листа для пользователся {self.username}')
#         req = {
#             ACTION: GET_CONTACTS,
#             TIME: time.time(),
#             USER: self.username
#         }
#         LOG.debug(f'Сформирован запрос {req}')
#         with socket_lock:
#             send_message(self.transport, req)
#             ans = get_message(self.transport)
#         LOG.debug(f'Получен ответ {ans}')
#         if RESPONSE in ans and ans[RESPONSE] == 202:
#             for contact in ans[LIST_INFO]:
#                 self.database.add_contact(contact)
#         else:
#             LOG.error('Не удалось обновить список контактов')
#
#     def add_contact(self,contact):
#         LOG.debug(f'Создание контакта {contact}')
#         req = {
#             ACTION: ADD_CONTACT,
#             TIME: time.time(),
#             USER: self.username,
#             ACCOUNT_NAME: contact
#         }
#         print(f'add_contact. req = {req}')
#         with socket_lock:
#             if self.transport:
#                 print('with socket_lock, self.transport')
#             send_message(self.transport, req)
#             print(f'send_message {req}')
#             try:
#                 msg = get_message(self.transport)
#                 print(msg)
#                 self.get_server_answer(msg)
#             except Exception as err:
#                 print(err)
#             print('get_server_answer')
#
#     def remove_contact(self, contact):
#         LOG.debug(f'Удаление контакта {contact}')
#         req = {
#             ACTION: REMOVE_CONTACT,
#             TIME: time.time(),
#             USER: self.username,
#             ACCOUNT_NAME: contact
#         }
#         with socket_lock:
#             send_message(self.transport, req)
#             self.get_server_answer(get_message(self.transport))
#
#     def transport_shutdown(self):
#         self.running = False
#         message = {
#             ACTION: EXIT,
#             TIME: time.time(),
#             ACCOUNT_NAME: self.username
#         }
#         with socket_lock:
#             try:
#                 send_message(self.transport, message)
#             except OSError:
#                 pass
#             LOG.debug('Транспорт завершает работу.')
#             time.sleep(0.5)
#
#     def send_message_(self, to, msg):
#         message = {
#             ACTION: MESSAGE,
#             SENDER: self.username,
#             DESTINATION: to,
#             TIME: time.time(),
#             MESSAGE_TEXT: msg
#         }
#         with socket_lock:
#             send_message(self.transport, message)
#             self.get_server_answer(get_message(self.transport))
#             LOG.info(f'Отправлено сообщение пользователю {to}')
#
#
#     def run(self):
#         LOG.debug('Запущен процесс приема/отправки сообщений на сервер')
#         while self.running:
#             time.sleep(1)
#             with socket_lock:
#                 try:
#                     self.transport.settimeout(0.5)
#                     message = get_message(self.transport)
#                 except OSError as err:
#                     if err.errno:
#                         LOG.critical('Потеряно соединение с сервером')
#                         self.running = False
#                         self.connection_lost.emit()
#                 except (ConnectionError, ConnectionAbortedError):
#                     LOG.debug('Потеряно соединение с сервером')
#                     self.running = False
#                     self.connection_lost.emit()
#                 else:
#                     LOG.debug(f'Принято сообщение с сервера: {message}')
#                     self.get_server_answer(message)
#                 finally:
#                     self.transport.settimeout(5)
#
#
import socket
import sys
import time
import logging
import json
import threading
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')
from common.utils import *
from common.variables import *
from common.errors import ServerError

# Логер и объект блокировки для работы с сокетом.
logger = logging.getLogger('client')
socket_lock = threading.Lock()


# Класс - Траннспорт, отвечает за взаимодействие с сервером
class ClientTransport(threading.Thread, QObject):
    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database = database
        # Имя пользователя
        self.username = username
        # Сокет для работы с сервером
        self.transport = None
        # Устанавливаем соединение:
        self.connection_init(port, ip_address)
        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                logger.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            logger.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            logger.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
            # Флаг продолжения работы транспорта.
        self.running = True

    # Функция инициализации соединения с сервером
    def connection_init(self, port, ip):
        # Инициализация сокета и сообщение серверу о нашем появлении
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут необходим для освобождения сокета.
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Установлено соединение с сервером')

        # Посылаем серверу приветственное сообщение и получаем ответ что всё нормально или ловим исключение.
        try:
            with socket_lock:
                send_message(self.transport, self.create_presence())
                self.process_server_ans(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise ServerError('Потеряно соединение с сервером!')

        # Раз всё хорошо, сообщение о установке соединения.
        logger.info('Соединение с сервером успешно установлено.')

    # Функция, генерирующая приветственное сообщение для сервера
    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username
            }
        }
        logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.username}')
        return out

    # Функция обрабатывающяя сообщения от сервера. Ничего не возращает. Генерирует исключение при ошибке.
    def process_server_ans(self, message):
        logger.debug(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            else:
                logger.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        elif ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and message[DESTINATION] == self.username:
            logger.debug(f'Получено сообщение от пользователя {message[SENDER]}:{message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER] , 'in' , message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])


    # Функция обновляющая контакт - лист с сервера
    def contacts_list_update(self):
        logger.debug(f'Запрос контакт листа для пользователся {self.name}')
        req = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        logger.debug(f'Сформирован запрос {req}')
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        logger.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            logger.error('Не удалось обновить список контактов.')

    # Функция обновления таблицы известных пользователей.
    def user_list_update(self):
        logger.debug(f'Запрос списка известных пользователей {self.username}')
        req = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            self.database.add_users(ans[LIST_INFO])
        else:
            logger.error('Не удалось обновить список известных пользователей.')

    # Функция сообщающая на сервер о добавлении нового контакта
    def add_contact(self, contact):
        logger.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    # Функция удаления клиента на сервере
    def remove_contact(self, contact):
        logger.debug(f'Удаление контакта {contact}')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    # Функция закрытия соединения, отправляет сообщение о выходе.
    def transport_shutdown(self):
        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        logger.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    # Функция отправки сообщения на сервер
    def send_message(self, to, message):
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            send_message(self.transport, message_dict)
            self.process_server_ans(get_message(self.transport))
            logger.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        logger.debug('Запущен процесс - приёмник собщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError, TypeError):
                    logger.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    logger.debug(f'Принято сообщение с сервера: {message}')
                    self.process_server_ans(message)
                finally:
                    self.transport.settimeout(5)