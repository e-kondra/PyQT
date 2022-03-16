'''
Модуль, отвечающий за транспортную систему клиентского приложения
'''
import socket
import time
import logging
import json
import threading
import hashlib
import hmac
import binascii

import PyQt5.QtCore

from common.utils import send_message, get_message
from common.errors import ServerError
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, PUBLIC_KEY, \
    RESPONSE, ERROR, DATA, RESPONSE_511, SENDER, MESSAGE, DESTINATION, \
    MESSAGE_TEXT, GET_CONTACTS, LIST_INFO, USERS_REQUEST, PUBLIC_KEY_REQUEST, \
    ADD_CONTACT, REMOVE_CONTACT, EXIT

LOG = logging.getLogger('client')
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, PyQt5.QtCore.QObject):
    '''
    Класс реализующий транспортную подсистему клиентского
    модуля. Отвечает за взаимодействие с сервером.
    '''
    # Сигналы новое сообщение и потеря соединения
    new_message = PyQt5.QtCore.pyqtSignal(dict)
    message_205 = PyQt5.QtCore.pyqtSignal()
    connection_lost = PyQt5.QtCore.pyqtSignal()

    def __init__(self, transport_dict):
        # Вызываем конструкторы предков
        threading.Thread.__init__(self)
        PyQt5.QtCore.QObject.__init__(self)

        # Класс База данных - работа с базой
        self.database = transport_dict['database']
        # Имя пользователя
        self.username = transport_dict['username']
        # Пароль
        self.password = transport_dict['passwd']
        # Сокет для работы с сервером
        self.transport = None
        # Набор ключей для шифрования
        self.keys = transport_dict['keys']
        # Устанавливаем соединение:
        self.connection_init(transport_dict['port'],
                             transport_dict['ip_address'])
        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                LOG.critical('Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            LOG.error(
                'Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            LOG.critical('Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
            # Флаг продолжения работы транспорта.
        self.running = True

    def connection_init(self, port, ip):
        '''Установка соединения с сервером.'''
        # Инициализация сокета и сообщение серверу о нашем появлении
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут необходим для освобождения сокета.
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если
        # удалось
        connected = False
        for i in range(5):
            LOG.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                LOG.debug("Connection established.")
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            LOG.critical('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        LOG.debug('Starting auth dialog.')

        # Запускаем процедуру авторизации
        # Получаем хэш пароля
        passwd_bytes = self.password.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        passwd_hash_string = binascii.hexlify(passwd_hash)

        LOG.debug(f'Passwd hash ready: {passwd_hash_string}')

        # Получаем публичный ключ и декодируем его из байтов
        pubkey = self.keys.publickey().export_key().decode('ascii')

        # Авторизируемся на сервере
        with socket_lock:
            presense = {
                ACTION: PRESENCE,
                TIME: time.time(),
                USER: {
                    ACCOUNT_NAME: self.username,
                    PUBLIC_KEY: pubkey
                }
            }
            LOG.debug(f"Presense message = {presense}")
            # Отправляем серверу приветственное сообщение.
            try:
                send_message(self.transport, presense)
                ans = get_message(self.transport)
                LOG.debug(f'Server response = {ans}.')
                # Если сервер вернул ошибку, бросаем исключение.
                if RESPONSE in ans:
                    if ans[RESPONSE] == 400:
                        raise ServerError(ans[ERROR])
                    elif ans[RESPONSE] == 511:
                        # Если всё нормально, то продолжаем процедуру
                        # авторизации.
                        ans_data = ans[DATA]
                        hash = hmac.new(passwd_hash_string, ans_data.encode('utf-8'), 'MD5')
                        digest = hash.digest()
                        my_ans = RESPONSE_511
                        my_ans[DATA] = binascii.b2a_base64(
                            digest).decode('ascii')
                        send_message(self.transport, my_ans)
                        self.process_server_ans(get_message(self.transport))
            except (OSError, json.JSONDecodeError) as err:
                LOG.debug(f'Connection error.', exc_info=err)
                raise ServerError('Сбой соединения в процессе авторизации.')

    def process_server_ans(self, message):
        '''Обработчик поступающих сообщений с сервера.'''
        LOG.debug(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.user_list_update()
                self.contacts_list_update()
                self.message_205.emit()
            else:
                LOG.error(
                    f'Принят неизвестный код '
                    f'подтверждения {message[RESPONSE]}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о
        # новом сообщении
        elif ACTION in message and message[ACTION] == MESSAGE\
                and SENDER in message and DESTINATION in message\
                and MESSAGE_TEXT in message \
                and message[DESTINATION] == self.username:
            LOG.debug(
                f'Получено сообщение от пользователя'
                f' {message[SENDER]}:{message[MESSAGE_TEXT]}')
            self.new_message.emit(message)

    def contacts_list_update(self):
        '''Обновление списка контактов с сервера'''
        self.database.contacts_clear()
        LOG.debug(f'Запрос контакт листа для пользователся {self.name}')
        req = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        LOG.debug(f'Сформирован запрос {req}')
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        LOG.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            LOG.error('Не удалось обновить список контактов.')

    def user_list_update(self):
        '''Обновление списка пользователей с сервера'''
        LOG.debug(f'Запрос списка известных пользователей {self.username}')
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
            LOG.error('Не удалось обновить список известных пользователей.')

    def key_request(self, user):
        '''Запрос с сервера публичного ключа пользователя.'''
        LOG.debug(f'Запрос публичного ключа для {user}')
        req = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: user
        }
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 511:
            return ans[DATA]
        else:
            LOG.error(f'Не удалось получить ключ собеседника{user}.')

    def add_contact(self, contact):
        '''Отправка на сервер сведения о добавлении контакта.'''
        LOG.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    def remove_contact(self, contact):
        '''Отправка на сервер сведения о удалении контакта.'''
        LOG.debug(f'Удаление контакта {contact}')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_server_ans(get_message(self.transport))

    def transport_shutdown(self):
        '''Уведомление сервера о завершении работы клиента'''
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
        LOG.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    def send_message(self, to, message):
        '''Отправка сообщения для пользователя на сервер'''
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOG.debug(f'Сформирован словарь сообщения: {message_dict}')
        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            send_message(self.transport, message_dict)
            self.process_server_ans(get_message(self.transport))
            LOG.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        '''Основной цикл работы транспортного потока.'''
        LOG.debug('Запущен процесс - приёмник собщений с сервера.')
        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то отправка может достаточно долго
            # ждать освобождения сокета.
            time.sleep(1)
            message = None
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        LOG.critical('Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except(ConnectionError, ConnectionAbortedError,
                       ConnectionResetError, json.JSONDecodeError, TypeError):
                    LOG.debug('Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                finally:
                    self.transport.settimeout(5)

            # Если сообщение получено, то вызываем функцию обработчик:
            if message:
                LOG.debug(f'Принято сообщение с сервера: {message}')
                self.process_server_ans(message)
