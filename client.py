import argparse
import sys
import threading
import time
from socket import *
import json
import logging
from threading import Thread

import logs.configs.client_log_config


from common.variables import *
from common.utils import send_message, get_message
from errors import ReqFieldMissingError, ServerError, IncorrectDataRecivedError
from decors import log
from metaclasses import ClientVerifier

LOG = logging.getLogger('client')

# Class is responsible for forming and sending messages from client
class Sender(threading.Thread,  metaclass=ClientVerifier):

    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
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
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOG.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            LOG.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            LOG.critical('Потеряно соединение с сервером.')
            sys.exit(1)

    def print_help(self):
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


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
                send_message(self.sock, self.create_exit_message())
                print('Завершение соединения.')
                LOG.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')


class Listener(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()


    def run(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            try:
                msg = get_message(self.sock)
                if ACTION in msg and msg[ACTION] == MESSAGE and SENDER in msg and DESTINATION in msg \
                        and MESSAGE_TEXT in msg and msg[DESTINATION] == self.account_name:
                    print(f'\nПолучено сообщение от пользователя {msg[SENDER]}: \n{msg[MESSAGE_TEXT]}')
                    LOG.info(f'Получено сообщение от пользователя {msg[SENDER]}: \n{msg[MESSAGE_TEXT]}')
                else:
                    LOG.error(f'Получено некорректное сообщение от сервера: {msg}')
            except IncorrectDataRecivedError:
                LOG.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                LOG.critical(f'Потеряно соединение с сервером.')
                break


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

    return server_address, server_port, client_name


def main():

    """Загружаем параметы коммандной строки"""
    server_address, server_port, client_name = arg_parser()

    if not client_name:
        client_name = input('Введите имя пользователя ')

    LOG.info(f'Запущен клиент со следующими параметрами: адрес {server_address}, порт {server_port}, имя пользователя {client_name}')

    # create socket and make connection

    try:
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_address, server_port))
        # client_socket.connect(('192.168.56.1', 8880))
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
        # прием сообщений
        THR_reseive = Listener(client_name,client_socket)
        THR_reseive.daemon = True
        THR_reseive.start()
        # отправка сообщений
        THR_send = Sender(client_name, client_socket )
        THR_send.daemon = True
        THR_send.start()

        while True:
            time.sleep(0.5)
            if THR_reseive.is_alive() and THR_send.is_alive():
                continue
            break



if __name__ == '__main__':
    main()
