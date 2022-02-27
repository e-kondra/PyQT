import argparse
import sys
import threading
import time
from socket import *
import json
import logging
from threading import Thread

from tabulate import tabulate

import logs.configs.client_log_config
from client_database import ClientDatabase

from common.variables import *
from common.utils import send_message, get_message
from errors import ReqFieldMissingError, ServerError, IncorrectDataRecivedError
from decors import log
from metaclasses import ClientVerifier


database_lock = threading.Lock()
sock_lock = threading.Lock()

LOG = logging.getLogger('client')

# Class is responsible for forming and sending messages from client
class Sender(threading.Thread,  metaclass=ClientVerifier):

    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()


    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    def create_message(self):
        """Функция запрашивает текст сообщения и возвращает его.
        Так же завершает работу при вводе подобной комманды
        """
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')

        with database_lock:
            if not self.database.check_user(to_user):
                LOG.error(f'Попытка отправки сообщения незарагистрированному пользователю: {to_user}')
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOG.debug(f'Сформирован словарь сообщения: {message_dict}')
        # Сохраняем сообщение
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                LOG.info(f'Отправлено сообщение для пользователя {to_user}')
            except OSError as err:
                if err.errno:
                    LOG.critical('Потеряно соединение с сервером.')
                    sys.exit(1)
                else:
                    LOG.error('Не удалось передать сообщение. Таймаут соединения')

    def print_help(self):
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history = self.database.get_history(to_user=self.account_name)
                for msg in history:
                    print(f'\nСообщение от пользователя: {msg[0]} от {msg[3]}:\n{msg[2]}')
                print(tabulate(history, headers = ['from user', 'to_user', '3', '2'],tablefmt = 'grid'))
            elif ask == 'out':
                history = self.database.get_history(from_user=self.account_name)
                for msg in history:
                    print(f'\nСообщение пользователю: {msg[1]} от {msg[3]}:\n{msg[2]}')
            else:
                history = self.database.get_history()
                for msg in history:
                    print(
                        f'\nСообщение от пользователя: {msg[0]}, пользователю {msg[1]} от {msg[3]}\n{msg[2]}')

    def edit_contact(self):
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            with database_lock:
                contact = input('Введите имя удаляемого контакта: ')
                if self.database.check_contact(contact):
                    self.database.del_contact(contact)
                else:
                    LOG.error('Попытка удаления не существующего клиента')
        elif ans == 'add':
            contact = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(contact):
                with database_lock:
                    self.database.add_contact(contact)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, contact)
                    except ServerError:
                        LOG.error('Не удалось отправить информацию на сервер.')

    def run(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except:
                        pass
                    LOG.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)
            elif command == 'edit':
                self.edit_contact()
            elif command == 'history':
                self.print_history()
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')


class Listener(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()


    def run(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            time.sleep(1)
            with sock_lock:
                try:
                    msg = get_message(self.sock)
                except IncorrectDataRecivedError:
                    LOG.error(f'Не удалось декодировать полученное сообщение.')
                except OSError as err:
                    if err.errno:
                        LOG.critical('Потеряно соединение с сервером.')
                        break
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError):
                    LOG.critical(f'Потеряно соединение с сервером.')
                    break
                else:
                    if ACTION in msg and msg[ACTION] == MESSAGE and SENDER in msg and DESTINATION in msg \
                            and MESSAGE_TEXT in msg and msg[DESTINATION] == self.account_name:
                        print(f'\nПолучено сообщение от пользователя {msg[SENDER]}: \n{msg[MESSAGE_TEXT]}')
                        with database_lock:
                            try:
                                self.database.save_message(msg[SENDER], self.account_name, msg[MESSAGE_TEXT])
                            except:
                                LOG.error('Ошибка взаимодействия с Базой Данных')
                        LOG.info(f'Получено сообщение от пользователя {msg[SENDER]}: \n{msg[MESSAGE_TEXT]}')
                    else:
                        LOG.error(f'Получено некорректное сообщение от сервера: {msg}')

# Запрос контакт листа
@log
def contacts_list_request(sock, name):
    LOG.debug(f'Запрос контакт листа для пользователся {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    LOG.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    LOG.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError
# Добавление пользователя в контакт лист
@log
def add_contact(sock, username, contact):
    LOG.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')

# Запрос списка известных пользователей
@log
def user_list_request(sock, username):
    LOG.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError

# Удаление пользователя из контакт листа
@log
def remove_contact(sock, username, contact):
    LOG.debug(f'Удаление контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')

@log
def make_presence(account_name='Guest'):
    '''generate clients presence request'''
    request = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    return request

@log
def get_answer_presence(msg):
    '''get answer from server'''
    if RESPONSE in msg:
        if msg[RESPONSE] == 200:
            return '200 : OK'
        LOG.debug('Получен ответ 400')
        return f'400 : {msg[ERROR]}'
    raise ReqFieldMissingError(RESPONSE)

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

    return server_address, server_port, client_name\

# Функция инициализатор базы данных. Запускается при запуске, загружает данные в базу с сервера.
@log
def database_load(sock, database, username):
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        LOG.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        LOG.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)

def main():
    # Сообщаем о запуске
    print('Консольный месседжер. Клиентский модуль.')
    # Загружаем параметы коммандной строки
    server_address, server_port, client_name = arg_parser()

    if not client_name:
        client_name = input('Введите имя пользователя ')

    LOG.info(f'Запущен клиент со следующими параметрами: адрес {server_address}, порт {server_port}, имя пользователя {client_name}')

    # create socket and make connection

    try:
        client_socket = socket(AF_INET, SOCK_STREAM)

        # Таймаут 1 секунда, необходим для освобождения сокета.
        client_socket.settimeout(1)

        # client_socket.connect((server_address, server_port))
        client_socket.connect(('192.168.56.1', 8880))
        # presence
        send_message(client_socket, make_presence(client_name))
        answer = get_answer_presence(get_message(client_socket))
        LOG.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
    except json.JSONDecodeError:
        LOG.error('Не удалось декодировать полученную Json строку.')
        sys.exit(1)
    except ServerError as error:
        LOG.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        LOG.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except ConnectionRefusedError:
        LOG.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    else:
        # Инициализация БД
        database = ClientDatabase(client_name)
        database_load(client_socket, database, client_name)

        THR_send = Sender(client_name, client_socket, database)
        THR_send.daemon = True
        THR_send.start()
        LOG.debug('Запущены процессы')
        # прием сообщений
        THR_reseive = Listener(client_name,client_socket, database)
        THR_reseive.daemon = True
        THR_reseive.start()
        # отправка сообщений


        while True:
            time.sleep(0.5)
            if THR_reseive.is_alive() and THR_send.is_alive():
                continue
            break



if __name__ == '__main__':
    main()
