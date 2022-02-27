import json
import unittest

from common.utils import get_message, send_message
from common.variables import RESPONSE, ERROR, ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, ENCODING


class TestSocket:
    '''
    Тестовый класс для тестирования отправки и получения,
    при создании требует словарь, который будет прогонятся
    через тестовую функцию
    '''

    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.receved_message = None

    def send(self, message):
        """
        переопределяем send (socket.send)
        """
        json_test_message = json.dumps(self.test_dict)
        self.encoded_message = json_test_message.encode(ENCODING)
        self.receved_message = message

    def recv(self, max_len):
        json_test_message = json.dumps(self.test_dict)
        return json_test_message.encode(ENCODING)


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.bad_response = {RESPONSE: 400, ERROR: 'Bad request'}
        self.good_response = {RESPONSE: 200}
        self.request = {ACTION: PRESENCE, TIME: 2.0, USER: {ACCOUNT_NAME: 'Guest'}}
        self.socket = TestSocket(self.request)

    def test_get_good_message(self):
        socket_ok = TestSocket(self.good_response)
        self.assertEqual(get_message(socket_ok), self.good_response)

    def test_get_bad_message(self):
        socket_bad = TestSocket(self.bad_response)
        self.assertEqual(get_message(socket_bad), self.bad_response)

    def test_send_message(self):
        send_message(self.socket,self.request)
        self.assertEqual(self.socket.encoded_message,self.socket.receved_message)

    def test_send_message_no_bytes(self):
        with self.assertRaises(Exception):
            send_message(self.socket, TestSocket('something'))


if __name__ == '__main__':
    unittest.main()


