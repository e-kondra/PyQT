import json
import sys
import logging
from datetime import time
from socket import socket, AF_INET, SOCK_STREAM
import time
from select import select
import argparse

from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, \
    MESSAGE_TEXT, MESSAGE, SENDER, DESTINATION, EXIT
from common.utils import get_message, send_message
from descriptors import Port, Host
from logs.configs import server_log_config
from decors import log
from metaclasses import ServerVerifier

LOG = logging.getLogger('server')


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(metaclass=ServerVerifier):
    listen_port = Port()
    listen_address = Host()

    def __init__(self, listen_address, listen_port):
        self.listen_address = listen_address
        self.listen_port = listen_port
        LOG.debug(f'listen_address = {listen_address}')
        self.clients = []
        self.message_list = []

        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        self.names = dict()


    def socket_init(self):
        # create servers socket
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind((self.listen_address, self.listen_port))
        server_socket.settimeout(0.8)

        self.server_socket = server_socket

        self.server_socket.listen()

    def clients_message_handling(self, msg, client):
        # 1.Сообщение о присутствии
        if ACTION in msg and msg[ACTION] == PRESENCE and TIME in msg and USER in msg:
            if msg[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[msg[USER][ACCOUNT_NAME]] = client
                LOG.info('Проверка сообщения в clients_message_handling успешна, ответ: 200')
                send_message(client, {RESPONSE: 200})
            else:
                LOG.warning('Проверка сообщения в check_message не успешна, ответ: Имя пользователя уже занято ')
                send_message(client, {RESPONSE: 400, ERROR: 'Имя пользователя уже занято'})
                self.clients.remove(client)
                client.close()
        # сообщение от одного клиента - другому
        elif ACTION in msg and msg[ACTION] == MESSAGE and TIME in msg and DESTINATION in msg \
                and SENDER in msg and MESSAGE_TEXT in msg:
            LOG.info('Получено сообщение в clients_message_handling, проверка успешна')
            self.message_list.append(msg)
            return
        # выход
        elif ACTION in msg and msg[ACTION] == EXIT and ACCOUNT_NAME in msg:
            self.clients.remove(self.names[msg[ACCOUNT_NAME]])
            self.names[msg[ACCOUNT_NAME]].close()
            del self.names[msg[ACCOUNT_NAME]]
            return
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
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = arg_parser()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port)
    # server = Server()
    server.run()

if __name__ == '__main__':
    main()